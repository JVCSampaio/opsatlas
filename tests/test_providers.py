import json

import httpx
import pytest

from opsatlas.config import Settings
from opsatlas.llm import answer
from opsatlas.retrieval import embed


@pytest.mark.parametrize(
    "payload",
    [
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "invalid JSON"}}]},
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"answer": "answer", "citation_ids": ["source"], "abstained": False}
                        )
                    }
                }
            ],
            "usage": {"completion_tokens": -1},
        },
    ],
)
def test_invalid_provider_responses_rejected(monkeypatch, payload):
    monkeypatch.setattr(
        "opsatlas.llm.httpx.post",
        lambda url, **kw: httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json=payload,
        ),
    )
    with pytest.raises(ValueError):
        answer("question", [{"id": "source", "text": "evidence"}], Settings(llm_mode="llm"))


def test_empty_evidence_does_not_invoke_provider(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Must not call the model")

    monkeypatch.setattr("opsatlas.llm.httpx.post", fail)
    assert answer("question", [], Settings(llm_mode="llm"))["abstained"]


@pytest.mark.parametrize(
    "rows",
    [
        [{"index": 0, "embedding": [1, 0]}, {"index": 0, "embedding": [0, 1]}],
        [{"index": 0, "embedding": [1, 0]}, {"index": 1, "embedding": [1]}],
        [{"index": 0, "embedding": [1, 0]}],
    ],
)
def test_bad_embedding_batches_rejected(monkeypatch, rows):
    monkeypatch.setattr(
        "opsatlas.retrieval.httpx.post",
        lambda url, **kw: httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"data": rows},
        ),
    )
    with pytest.raises(ValueError):
        embed(["alpha", "beta"], Settings(embedding_model="test-embeddings"))


def test_semantic_provider_preserves_batch_order(monkeypatch):
    monkeypatch.setattr(
        "opsatlas.retrieval.httpx.post",
        lambda url, **kw: httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "data": [
                    {"index": 1, "embedding": [0, 1]},
                    {"index": 0, "embedding": [1, 0]},
                ]
            },
        ),
    )
    assert embed(["alpha", "beta"], Settings(embedding_model="test-embeddings")) == [[1, 0], [0, 1]]
