import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from opsatlas.api import create_app
from opsatlas.config import Settings
from opsatlas.db import Audit, Chunk, Outbox
from opsatlas.retrieval import index_document


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path}/test.db"))
    with TestClient(app) as client:
        yield client


def test_recruiter_journey(client):
    assert client.get("/health/ready").status_code == 200
    assert client.post("/api/demo/seed").status_code == 200
    assert len(client.get("/api/documents").json()) == 3
    result = client.post(
        "/api/ask", json={"question": "Atraso dos consumidores Kafka número de partições"}
    )
    assert result.status_code == 200
    assert result.json()["citations"][0]["source"] == "runbooks/kafka-consumer-lag"
    assert "número de partições" in result.json()["answer"]
    assert not result.json()["abstained"]
    assert result.headers["X-Request-ID"]
    assert client.post("/api/evaluations").json()["passed"] == 4
    assert "opsatlas_answers_total" in client.get("/metrics").text


def test_unknown_question_abstains(client):
    client.post("/api/demo/seed")
    result = client.post("/api/ask", json={"question": "Intergalactic chess championship"}).json()
    assert result["abstained"]
    assert result["citations"] == []


def test_tenant_isolation(client):
    client.post("/api/demo/seed", headers={"X-Tenant": "alpha"})
    assert client.get("/api/documents", headers={"X-Tenant": "beta"}).json() == []
    result = client.post(
        "/api/ask", headers={"X-Tenant": "beta"}, json={"question": "Kafka consumer lag"}
    )
    assert result.json()["abstained"]
    assert client.get("/api/overview", headers={"X-Tenant": "beta"}).json()["chunks"] == 0


def test_revision_and_duplicate_submission(client):
    payload = {
        "title": "Rollback",
        "source": "runbooks/rollback",
        "content": "Rollback threshold is five minutes.",
    }
    first = client.post("/api/documents", json=payload).json()
    repeat = client.post("/api/documents", json=payload).json()
    assert repeat["unchanged"] and repeat["revision"] == 1
    payload["content"] = "Rollback threshold is ten minutes."
    second = client.post("/api/documents", json=payload).json()
    assert second["id"] == first["id"] and second["revision"] == 2
    answer = client.post("/api/ask", json={"question": "Rollback threshold"}).json()
    assert "ten minutes" in answer["answer"]
    assert answer["citations"][0]["revision"] == 2
    with client.app.state.sessions() as session:
        assert len(list(session.scalars(select(Chunk)))) == 1


def test_queued_ingestion_stale_and_duplicate_events(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path}/queue.db", ingestion_mode="kafka")
    app = create_app(settings)
    with TestClient(app) as client:
        data = {"title": "Queue", "source": "queue", "content": "Queue original behavior"}
        doc = client.post("/api/documents", json=data).json()
        assert doc["status"] == "queued"
        data["content"] = "Queue updated behavior"
        client.post("/api/documents", json=data)
        with app.state.sessions.begin() as session:
            assert not index_document(session, doc["id"], 1, settings)
            assert index_document(session, doc["id"], 2, settings)
        with app.state.sessions.begin() as session:
            assert not index_document(session, doc["id"], 2, settings)
        assert (
            "updated"
            in client.post("/api/ask", json={"question": "Queue behavior"}).json()["answer"]
        )


def test_auth_and_validation(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path}/auth.db", api_key="test-key"))
    with TestClient(app) as client:
        assert client.get("/api/documents").status_code == 401
        assert (
            client.get("/api/documents", headers={"Authorization": "Bearer test-key"}).status_code
            == 200
        )
        assert (
            client.get(
                "/api/documents",
                headers={"Authorization": "Bearer test-key", "X-Tenant": "../escape"},
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/ask", headers={"Authorization": "Bearer test-key"}, json={"question": ""}
            ).status_code
            == 422
        )


def test_llm_citation_contract(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path}/llm.db", llm_mode="llm")
    app = create_app(settings)
    with TestClient(app) as client:
        client.post("/api/demo/seed")
        with app.state.sessions() as session:
            chunk_id = session.scalar(
                select(Chunk.id).where(Chunk.text.like("%Atraso dos consumidores Kafka%"))
            )

        def provider(url, **kwargs):
            assert len(json.loads(kwargs["json"]["messages"][1]["content"])["evidence"]) > 0
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "Scale up to partition count.",
                                        "citation_ids": [chunk_id],
                                        "abstained": False,
                                    }
                                )
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 20},
                },
            )

        monkeypatch.setattr("opsatlas.llm.httpx.post", provider)
        result = client.post("/api/ask", json={"question": "Kafka consumer lag"})
        assert result.status_code == 200 and result.json()["usage"]["completion_tokens"] == 20
        with app.state.sessions() as session:
            assert session.scalar(select(Audit).where(Audit.kind == "answer.created"))


def test_llm_rejects_invented_sources(tmp_path, monkeypatch):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path}/bad.db", llm_mode="llm"))
    with TestClient(app) as client:
        client.post("/api/demo/seed")
        monkeypatch.setattr(
            "opsatlas.llm.httpx.post",
            lambda url, **kwargs: httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "answer": "Invented",
                                        "citation_ids": ["fake"],
                                        "abstained": False,
                                    }
                                )
                            }
                        }
                    ]
                },
            ),
        )
        assert client.post("/api/ask", json={"question": "Kafka consumer lag"}).status_code == 502


def test_outbox_recorded_with_document(client):
    client.post("/api/demo/seed")
    with client.app.state.sessions() as session:
        events = list(session.scalars(select(Outbox)))
        assert len(events) == 3 and all(e.published for e in events)
