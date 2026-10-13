# Validation evidence

Verified on 2026-10-13. Tested application revision: [`a97f307`](https://github.com/JVCSampaio/opsatlas/commit/a97f3073cd09ff604caf076c97e79d92442cf2d9). [All four CI jobs passed](https://github.com/JVCSampaio/opsatlas/actions/runs/38473866500).

| Check | Observed result |
| --- | --- |
| Python | 23 tests passed; local statement coverage 89%; Ruff lint/format passed |
| Angular | Production build passed; estimated initial transfer about 40 kB |
| Browser | Two Chromium journeys passed on Windows and Linux; desktop evidence/abstention/evaluation and mobile upload/layout |
| Package | Python wheel and source distribution built successfully |
| Compose | Real PostgreSQL, Kafka, indexing worker and MongoDB audit projection passed black-box smoke |
| Observability | Prometheus scraped the API; provisioned four-panel Grafana dashboard verified through its API |
| Airflow | DAG parsed, `seed` and `evaluate` executed through Airflow's DAG test engine; DagRun finished `success` with 4/4 retrieval checks |
| Kubernetes | Isolated kind cluster created, persistent data services deployed, API/worker/web rolled out; Kafka ingestion and retrieval smoke passed |

The host Docker engine reported unavailable virtualization. Containers, Airflow and Kubernetes were therefore executed on Linux GitHub Actions runners. They were not claimed as locally executed on Windows. Screenshots came from real browser tests.

- [Python job](https://github.com/JVCSampaio/opsatlas/actions/runs/38473866500/job/115559547689)
- [Browser job](https://github.com/JVCSampaio/opsatlas/actions/runs/38473866500/job/115559547375)
- [Integration + Airflow job](https://github.com/JVCSampaio/opsatlas/actions/runs/38473866500/job/115559547551)
- [Kubernetes job](https://github.com/JVCSampaio/opsatlas/actions/runs/38473866500/job/115559547858)

Covered regressions include tenant scoping, document revisions, duplicate/stale indexing events, acknowledged outbox publishing, audit replay, invalid provider payloads, invented citations, invalid embedding batches and no-evidence abstention. A dependency emits a Starlette warning about the legacy httpx test adapter; the tests currently pass.

No local model server was active during the initial validation. The LLM HTTP adapter has provider-response contract tests, including token usage and invalid citations. This is not a measured evaluation of a real model's answer quality. The default demonstrated answer mode is extractive.

The four-case sample retrieval suite is visible and synthetic. It is a regression smoke, not an unseen benchmark. This project makes no economic or production-scale claims.
