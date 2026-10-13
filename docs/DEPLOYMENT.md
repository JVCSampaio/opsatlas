# Deployment

## Docker Compose

```sh
docker compose up -d --build --wait --wait-timeout 300
uv run python scripts/smoke.py
docker compose logs worker
docker compose --profile airflow up -d airflow
```

Compose binds published services to localhost. Database, Kafka, MongoDB and Tempo are private to its network. `POSTGRES_PASSWORD`, `GRAFANA_PASSWORD` and `OPSATLAS_API_KEY` can be set through `.env`. The sample database password must remain URL-safe unless the connection URL is changed to percent-encode it. Changing a PostgreSQL password environment variable does not rotate an existing database user's password.

Stop without deleting data: `docker compose --profile airflow down`. Volumes retain the SQL corpus, broker records and Mongo projection. Do not use `down -v` unless intentionally resetting all demonstration data.

## Kubernetes local cluster

Requires a working Docker Linux engine, kind and kubectl. The manifest is explicitly a **development overlay**, with fixture credentials and single-instance data services.

```sh
docker build -t opsatlas-api:local .
docker build -t opsatlas-web:local web
kind create cluster --name opsatlas
kind load docker-image opsatlas-api:local opsatlas-web:local --name opsatlas
kubectl apply -k infra/k8s
kubectl -n opsatlas rollout status deployment/api --timeout=300s
kubectl -n opsatlas rollout status deployment/worker --timeout=300s
kubectl -n opsatlas rollout status deployment/web --timeout=300s
kubectl -n opsatlas port-forward service/web 4200:80
```

For black-box API validation, another terminal can forward `service/api 8000:8000` and run `uv run python scripts/smoke.py`. The web proxy targets the `api` service, so the browser flow works without exposing databases.

The supplied Kubernetes overlay covers the application and data path. Airflow and observability run in the Compose demonstration; a cluster deployment should use their upstream charts rather than pretending the local overlay deploys them.

## CI and release

Pushes and PRs run Python lint/tests, the Angular production build, real-browser journeys and the container integration smoke. Tags such as `v0.1.0` build and publish API/web images to GHCR. Container publication is automated; cluster rollout is an explicit operator action. This prevents repository pushes from modifying an unknown live cluster.

For external use replace demo credentials with Secrets or an external secret store, add tenant-aware authentication and TLS, database migration procedures, quotas/rate limits, network policies, broker authentication and backups. Readiness checks SQL availability; it does not certify Kafka, Mongo or LLM availability. Pending ingestion remains visible as `queued` when the worker is unavailable.
