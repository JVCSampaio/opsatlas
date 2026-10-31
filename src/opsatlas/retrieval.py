import hashlib
import math
import re
import unicodedata
from collections import Counter

import httpx
from sqlalchemy import delete, select

from opsatlas.db import Chunk, Document

# Function words are not evidence: a question that shares only "da" or "the" with a
# runbook must abstain. Entries are accent-free because terms() strips accents first.
STOP = set(
    """
    a an and are as at be by can do does for from how in is it of on or that the this
    to was what when where which who why with
    o os as um uma uns umas de do da dos das em no na nos nas num numa ao aos por pelo
    pela pelos pelas para pra com sem sob sobre entre ate apos ou mas nem que se como
    qual quais quanto quantos quando onde quem porque eu voce ele ela eles elas isso
    isto esse essa esses essas este esta estes estas meu minha seu sua seus suas sao
    ser foi estao ha tem nao
    """.split()
)


def terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return [t for t in re.findall(r"\w+", normalized) if t not in STOP and len(t) > 1]


def lexical_vector(text: str) -> list[float]:
    """Offline lexical feature hashing; deliberately not a semantic embedding model."""
    vector = [0.0] * 256
    for token, count in Counter(terms(text)).items():
        bucket = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") % 256
        vector[bucket] += count
    length = math.sqrt(sum(x * x for x in vector)) or 1
    return [x / length for x in vector]


def embed(texts: list[str], settings) -> list[list[float]]:
    if not settings.embedding_model:
        return [lexical_vector(text) for text in texts]
    response = httpx.post(
        f"{settings.llm_base_url.rstrip('/')}/embeddings",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={"model": settings.embedding_model, "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    rows = sorted(response.json()["data"], key=lambda row: row["index"])
    if len(rows) != len(texts):
        raise ValueError("Embedding provider returned an incomplete batch")
    if [row["index"] for row in rows] != list(range(len(texts))):
        raise ValueError("Embedding provider returned invalid batch indices")
    vectors = [row["embedding"] for row in rows]
    if not vectors or any(not v or any(not math.isfinite(x) for x in v) for v in vectors):
        raise ValueError("Invalid embedding vector")
    if len({len(vector) for vector in vectors}) != 1:
        raise ValueError("Embedding provider returned inconsistent dimensions")
    return vectors


def profile(settings) -> str:
    return settings.embedding_model or "lexical-hash-v2"


def split_chunks(text: str, size: int = 900) -> list[str]:
    chunks, current = [], ""
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        for offset in range(0, len(paragraph), size):
            part = paragraph[offset : offset + size]
            if len(current) + len(part) + 2 > size and current:
                chunks.append(current)
                current = ""
            current = (current + "\n\n" + part).strip()
    if current:
        chunks.append(current)
    return chunks


def index_document(session, document_id: str, revision: int, settings) -> bool:
    # Lock serializes duplicate deliveries and updates on PostgreSQL. A repeated
    # event for an indexed revision is a no-op; old events cannot overwrite it.
    doc = session.scalar(select(Document).where(Document.id == document_id).with_for_update())
    if not doc or doc.revision != revision or doc.indexed_revision == revision:
        return False
    texts = split_chunks(doc.content)
    vectors = embed(texts, settings)
    session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    for i, (text, vector) in enumerate(zip(texts, vectors, strict=True)):
        session.add(
            Chunk(
                id=f"{doc.id}:{revision}:{i}",
                document_id=doc.id,
                tenant=doc.tenant,
                revision=revision,
                text=text,
                vector=vector,
                embedding_profile=profile(settings),
            )
        )
    doc.status, doc.indexed_revision = "ready", revision
    return True


def retrieve(session, tenant: str, question: str, settings, limit: int = 4) -> list[dict]:
    query_terms = set(terms(question))
    if not query_terms:
        return []
    query_vector = embed([question], settings)[0]
    rows = session.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Chunk.tenant == tenant,
            Document.tenant == tenant,
            Document.status == "ready",
            Chunk.revision == Document.revision,
            Chunk.embedding_profile == profile(settings),
        )
    ).all()
    scored = []
    for chunk, doc in rows:
        overlap = len(query_terms & set(terms(chunk.text))) / len(query_terms)
        if len(query_vector) != len(chunk.vector):
            continue
        denominator = math.sqrt(sum(x * x for x in query_vector) * sum(x * x for x in chunk.vector))
        cosine = sum(a * b for a, b in zip(query_vector, chunk.vector, strict=True)) / (
            denominator or 1
        )
        # Offline mode requires actual word overlap, avoiding hash-collision evidence.
        if (not settings.embedding_model and overlap == 0) or (overlap == 0 and cosine < 0.5):
            continue
        score = 0.65 * overlap + 0.35 * max(0, cosine)
        scored.append(
            {
                "id": chunk.id,
                "document_id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "revision": chunk.revision,
                "text": chunk.text,
                "score": round(score, 4),
            }
        )
    return sorted(scored, key=lambda row: (-row["score"], row["id"]))[:limit]
