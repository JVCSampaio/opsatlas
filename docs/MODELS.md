# Model configuration

Copy `.env.example` to `.env` and configure:

```dotenv
OPSATLAS_LLM_MODE=llm
OPSATLAS_LLM_BASE_URL=http://127.0.0.1:8081/v1
OPSATLAS_LLM_MODEL=your-served-model-id
OPSATLAS_LLM_API_KEY=
# Optional: use a served embedding model to enable semantic vectors.
OPSATLAS_EMBEDDING_MODEL=your-embedding-model-id
```

Restart the API (and worker in the full-stack profile). Inside Docker use `http://host.docker.internal:8081/v1` for a model on the host. A hosted OpenAI-compatible endpoint works through the same adapter; keep its key in environment variables. No paid API call is needed for the default demo.

The chat adapter requires `/chat/completions` with JSON object output. It validates `answer`, `citation_ids`, and `abstained`; malformed output, missing required citations or invented IDs return HTTP 502 rather than a fabricated fallback. Empty retrieval skips generation entirely. Sources are framed as untrusted data, but this does not constitute a complete prompt-injection defense.

The embedding adapter uses `/embeddings`, checks batch length, finite values, vector dimensions at retrieval and model identity. Without an embedding model, `lexical-hash-v1` is deterministic word-feature hashing, **not a semantic model**. Scores combine lexical overlap (65%) and cosine similarity (35%). Offline queries require actual token overlap, guarding against hash-collision matches.

An embedding profile change requires reindexing: increment the document revision by submitting changed content, or rebuild the demo database. For a real corpus, add a controlled batch reindex migration. Do not silently mix model vectors.

Token metrics come from the provider's `usage` response. Zero generated tokens in extractive mode means no LLM was invoked. This project does not claim measured Codex quota savings or API cost reduction.
