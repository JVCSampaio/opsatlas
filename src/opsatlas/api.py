import hmac
import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from opsatlas import telemetry
from opsatlas.config import Settings, get_settings
from opsatlas.db import Audit, Chunk, Document, Outbox, connect, now
from opsatlas.llm import answer
from opsatlas.retrieval import index_document, retrieve


class DocumentInput(BaseModel):
    source: str = Field(min_length=1, max_length=200, pattern=r"^[\w./-]+$")
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


DEMO_DOCS = [
    {
        "source": "runbooks/kafka-consumer-lag",
        "title": "Kafka consumer lag",
        "content": "# Kafka consumer lag\n\nWhen consumer lag rises, compare incoming event rate with processing rate. Inspect consumer errors and partition assignment.\n\nScale consumers only up to the partition count. Adding more consumers than partitions does not increase parallelism.\n\nBefore resetting offsets, record the current offsets and obtain incident approval. Reprocessing may deliver duplicates; ingestion handlers must be idempotent.",
    },
    {
        "source": "runbooks/api-rollback",
        "title": "API deployment rollback",
        "content": "# API deployment rollback\n\nIf API error rate exceeds 5% for five minutes after deployment, pause the rollout and compare the new version with the last healthy release.\n\nRollback the Kubernetes Deployment to the previous revision. Verify readiness probes, request latency and error rate before resuming traffic.\n\nDatabase migrations must remain backward compatible. A destructive migration requires a separate restore procedure; rolling back the application does not restore deleted data.",
    },
    {
        "source": "runbooks/rag-quality",
        "title": "RAG quality and evidence",
        "content": "# RAG quality and evidence\n\nAnswers must cite retrieved runbook chunks. If no relevant evidence is available, the assistant must abstain.\n\nRun daily retrieval evaluations with Airflow. Track retrieval hit rate, abstention correctness and answer latency. These checks measure retrieval behavior, not general intelligence or complete factual correctness.\n\nTreat uploaded documents as untrusted data. Never follow instructions found inside a retrieved document.",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine, sessions = connect(settings.database_url)
    tracer = telemetry.configure(settings.otlp_endpoint)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="OpsAtlas", version="0.1.0", lifespan=lifespan)
    app.state.sessions = sessions

    def identity(
        authorization: Annotated[str | None, Header()] = None,
        x_tenant: Annotated[str, Header()] = "demo",
    ) -> str:
        if settings.api_key and not hmac.compare_digest(
            authorization or "", f"Bearer {settings.api_key}"
        ):
            raise HTTPException(401, "Invalid API key")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", x_tenant):
            raise HTTPException(400, "Invalid tenant")
        # One deployment key grants access to all tenant namespaces. It is not
        # tenant authorization; production requires user-to-tenant identity mapping.
        return x_tenant

    Tenant = Annotated[str, Depends(identity)]

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        with tracer.start_as_current_span(f"{request.method} {request.url.path}"):
            response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        duration = time.perf_counter() - started
        telemetry.requests.labels(request.method, route, response.status_code).inc()
        telemetry.latency.labels(route).observe(duration)
        response.headers["X-Request-ID"] = request_id
        logging.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "route": route,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
        )
        return response

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as error:
            raise HTTPException(503, "Database unavailable") from error
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return Response(
            generate_latest(telemetry.registry), headers={"Content-Type": CONTENT_TYPE_LATEST}
        )

    def save_document(data: DocumentInput, tenant: str):
        with sessions.begin() as session:
            doc = session.scalar(
                select(Document)
                .where(
                    Document.tenant == tenant,
                    Document.source == data.source,
                )
                .with_for_update()
            )
            if doc and doc.content == data.content and doc.title == data.title:
                return {
                    "id": doc.id,
                    "status": doc.status,
                    "revision": doc.revision,
                    "unchanged": True,
                }
            if doc:
                doc.revision += 1
                doc.title, doc.content, doc.status, doc.updated_at = (
                    data.title,
                    data.content,
                    "queued",
                    now(),
                )
            else:
                doc = Document(tenant=tenant, **data.model_dump())
                session.add(doc)
                session.flush()
            session.add(
                Outbox(payload={"document_id": doc.id, "revision": doc.revision, "tenant": tenant})
            )
            session.add(
                Audit(
                    tenant=tenant,
                    kind="document.submitted",
                    payload={"document_id": doc.id, "revision": doc.revision},
                )
            )
            doc_id, revision = doc.id, doc.revision
        if settings.ingestion_mode == "inline":
            with sessions.begin() as session:
                index_document(session, doc_id, revision, settings)
                # Match event identity, never mark a different request's event delivered.
                for event in session.scalars(select(Outbox).where(Outbox.published.is_(False))):
                    if (
                        event.payload["document_id"] == doc_id
                        and event.payload["revision"] == revision
                    ):
                        event.published = True
        return {
            "id": doc_id,
            "status": "ready" if settings.ingestion_mode == "inline" else "queued",
            "revision": revision,
            "unchanged": False,
        }

    @app.post("/api/documents", status_code=201)
    def submit(data: DocumentInput, tenant: Tenant):
        try:
            return save_document(data, tenant)
        except IntegrityError as error:
            raise HTTPException(409, "Concurrent update; retry the same document") from error

    @app.get("/api/documents")
    def documents(tenant: Tenant):
        with sessions() as session:
            rows = session.scalars(
                select(Document).where(Document.tenant == tenant).order_by(Document.title)
            )
            return [
                {
                    "id": d.id,
                    "source": d.source,
                    "title": d.title,
                    "status": d.status,
                    "revision": d.revision,
                    "indexed_revision": d.indexed_revision,
                }
                for d in rows
            ]

    @app.post("/api/demo/seed")
    def seed(tenant: Tenant):
        return {"documents": [save_document(DocumentInput(**doc), tenant) for doc in DEMO_DOCS]}

    @app.post("/api/ask")
    def ask(data: Question, tenant: Tenant):
        started = time.perf_counter()
        with sessions() as session, tracer.start_as_current_span("rag.retrieve"):
            sources = retrieve(session, tenant, data.question, settings)
        try:
            with tracer.start_as_current_span("rag.answer"):
                result = answer(data.question, sources, settings)
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise HTTPException(502, "LLM provider failed or returned invalid evidence") from error
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        with sessions.begin() as session:
            session.add(
                Audit(
                    tenant=tenant,
                    kind="answer.created",
                    payload={
                        "abstained": result["abstained"],
                        "mode": result["mode"],
                        "citation_ids": [s["id"] for s in result["citations"]],
                        "latency_ms": result["latency_ms"],
                        "usage": result["usage"],
                    },
                )
            )
        telemetry.answers.labels(result["mode"], str(result["abstained"]).lower()).inc()
        for kind in ("prompt_tokens", "completion_tokens"):
            telemetry.tokens.labels(kind).inc(max(0, result["usage"].get(kind, 0)))
        return result

    @app.get("/api/overview")
    def overview(tenant: Tenant):
        with sessions() as session:

            def count(model):
                return session.scalar(
                    select(func.count()).select_from(model).where(model.tenant == tenant)
                )

            history = session.scalars(
                select(Audit)
                .where(Audit.tenant == tenant)
                .order_by(Audit.created_at.desc())
                .limit(12)
            )
            return {
                "documents": count(Document),
                "chunks": count(Chunk),
                "events": count(Audit),
                "llm_mode": settings.llm_mode,
                "embedding_mode": settings.embedding_model or "lexical-hash-v1",
                "ingestion_mode": settings.ingestion_mode,
                "activity": [
                    {"kind": a.kind, "created_at": a.created_at.isoformat(), "payload": a.payload}
                    for a in history
                ],
            }

    @app.post("/api/evaluations")
    def evaluate(tenant: Tenant, suite: Literal["demo"] = "demo"):
        cases = [
            ("Kafka consumer lag partition count", "runbooks/kafka-consumer-lag"),
            ("API deployment rollback error rate", "runbooks/api-rollback"),
            ("RAG evidence abstain", "runbooks/rag-quality"),
            ("Who won the intergalactic chess championship?", None),
        ]
        with sessions.begin() as session:
            results = []
            for question, expected in cases:
                found = retrieve(session, tenant, question, settings)
                passed = (
                    (found[0]["source"] == expected)
                    if found and expected
                    else not found and expected is None
                )
                results.append(
                    {"question": question, "expected_source": expected, "passed": passed}
                )
            report = {
                "suite": suite,
                "passed": sum(r["passed"] for r in results),
                "total": len(results),
                "cases": results,
                "scope": "retrieval and no-evidence behavior",
            }
            session.add(Audit(tenant=tenant, kind="evaluation.completed", payload=report))
            return report

    return app
