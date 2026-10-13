# Architecture decisions

## Runnable without external infrastructure

The offline profile uses SQLite, inline indexing and extractive answers. It shares the same API and retrieval implementation as the event profile. This makes the first reviewer journey possible without GPU, keys or containers. Angular 21 is compatible with Node 24; the choice follows the [official compatibility matrix](https://angular.dev/reference/versions).

## Transactional outbox rather than dual writes

Saving a document and publishing directly to Kafka leaves a gap if one operation succeeds and the other fails. Instead, the document revision, audit record and pending event commit together in SQL. The worker publishes and waits for acknowledgement before marking an event sent. Delivery remains at least once, not exactly once. Consumer offsets are committed only after indexing commits.

PostgreSQL row locks serialize revision indexing and concurrent updates. Stable chunk IDs and indexed revision guards make duplicate messages harmless. SQLite is intended for the single-process demo; it does not provide PostgreSQL's row-lock concurrency guarantees.

## SQL authority, MongoDB projection

SQL holds operational truth, including the audit export state. MongoDB stores a queryable audit projection. Export uses UUID-based upserts; a crash between Mongo acknowledgement and SQL commit can safely replay. Raw question and answer bodies are not stored in the audit stream, reducing unnecessary content retention.

## Visible model boundaries

Sources are selected before inference, bounded to four chunks and 6,000 context characters. Generation must name known retrieved chunk IDs. Missing evidence causes abstention without a model call. The runtime does not assert that a cited answer is factually proven. Retrieval evaluations and model-answer correctness are separate questions.

## Observable workflow

API counters expose normalized route labels, avoiding question/tenant identifiers in Prometheus labels. Histograms record request latency; generation usage comes from provider accounting. OpenTelemetry spans cover HTTP requests, retrieval and answering. Grafana provisions Prometheus and Tempo; trace exploration is available through the Tempo datasource. Logs include a generated request ID and never include API keys or corpus text.

## Deliberate scale boundary

Ranking currently scans tenant chunks; it is suitable for a small demonstration corpus. SQL schema initialization uses `create_all` for the initial version. A production evolution should introduce reviewed Alembic migrations, server-side BM25/vector search, per-user tenant claims, worker lag monitoring, DLQ handling, and infrastructure managed independently from the application. Single-node Kafka KRaft and Airflow standalone are local demonstration configurations. See [Kafka's Docker examples](https://github.com/apache/kafka/tree/trunk/docker/examples) and [Airflow's Docker documentation](https://airflow.apache.org/docs/apache-airflow/3.2.2/howto/docker-compose/).
