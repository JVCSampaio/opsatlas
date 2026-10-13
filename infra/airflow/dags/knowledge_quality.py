"""Daily retrieval quality gate using the same API contract as the UI."""

import json
import os
import time
import urllib.request
from datetime import datetime

from airflow.sdk import dag, task


def request(path, body=None):
    url = os.environ.get("OPSATLAS_API_URL", "http://api:8000") + path
    headers = {"Content-Type": "application/json", "X-Tenant": "demo"}
    key = os.environ.get("OPSATLAS_API_KEY", "")
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None, headers=headers
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


@dag(
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["rag", "quality"],
    default_args={"retries": 1},
)
def knowledge_quality():
    @task
    def seed():
        request("/api/demo/seed", {})
        for _ in range(60):
            if all(d["status"] == "ready" for d in request("/api/documents")):
                return "indexed"
            time.sleep(2)
        raise RuntimeError("Ingestion did not finish within 120 seconds")

    @task
    def evaluate(_indexed):
        report = request("/api/evaluations", {})
        if report["passed"] != report["total"]:
            raise ValueError("Retrieval regression: " + json.dumps(report))
        return report

    evaluate(seed())


knowledge_quality()
