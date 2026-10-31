import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SET_PATH = ROOT / "evals" / "retrieval.json"
DEMO_SOURCES = {
    "runbooks/kafka-consumer-lag",
    "runbooks/api-rollback",
    "runbooks/rag-quality",
}


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "eval_retrieval", ROOT / "scripts" / "eval_retrieval.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retrieval_set_is_labeled_from_the_demo_runbooks():
    data = load_runner().load_set(SET_PATH)
    assert data["name"] == "runbooks-demo-v1"
    assert len(data["cases"]) == 20
    assert len({case["id"] for case in data["cases"]}) == 20
    for case in data["cases"]:
        assert case["question"].strip()
        assert case["expected_source"] is None or case["expected_source"] in DEMO_SOURCES
    assert sum(case["expected_source"] is None for case in data["cases"]) == 3


def test_retrieval_set_measured_outcome():
    report = load_runner().run_set()
    assert report["embedding_mode"] == "lexical-hash-v2"
    assert report["llm_mode"] == "extractive"
    assert report["documents_ready"] == 3
    assert report["with_expected_source"] == 17
    assert report["abstention_cases"] == 3
    assert [row["id"] for row in report["cases"] if not row["passed"]] == []
    assert report["passed"] == report["total"] == 20
