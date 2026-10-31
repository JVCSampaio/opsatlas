"""Run the checked-in retrieval set against the local extractive API.

Uses the demo runbooks, SQLite and lexical search. Does not call an LLM.
"""

import json
import platform
import statistics
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from opsatlas.api import create_app
from opsatlas.config import Settings

ROOT = Path(__file__).resolve().parents[1]
SET_PATH = ROOT / "evals" / "retrieval.json"


def load_set(path: Path = SET_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_set(data: dict | None = None) -> dict:
    data = data or load_set()
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(
            Settings(
                database_url=f"sqlite:///{directory}/eval.db",
                ingestion_mode="inline",
                llm_mode="extractive",
                embedding_model="",
                api_key="",
                llm_api_key="",
                otlp_endpoint="",
            )
        )
        with TestClient(app) as client:
            seeded = client.post("/api/demo/seed")
            seeded.raise_for_status()
            overview = client.get("/api/overview").json()
            rows = []
            for case in data["cases"]:
                response = client.post("/api/ask", json={"question": case["question"]})
                response.raise_for_status()
                payload = response.json()
                citations = payload["citations"]
                obtained = citations[0]["source"] if citations else None
                expected = case["expected_source"]
                if expected is None:
                    passed = payload["abstained"] is True and obtained is None
                else:
                    passed = obtained == expected and payload["abstained"] is False
                rows.append(
                    {
                        "id": case["id"],
                        "question": case["question"],
                        "expected_source": expected,
                        "obtained_source": obtained,
                        "abstained": payload["abstained"],
                        "passed": passed,
                        "latency_ms": payload["latency_ms"],
                        "mode": payload["mode"],
                    }
                )
    latencies = [row["latency_ms"] for row in rows]
    with_source = [row for row in rows if row["expected_source"] is not None]
    abstentions = [row for row in rows if row["expected_source"] is None]
    return {
        "set": data["name"],
        "python": platform.python_version(),
        "documents_ready": overview["documents"],
        "embedding_mode": overview["embedding_mode"],
        "llm_mode": overview["llm_mode"],
        "ingestion_mode": overview["ingestion_mode"],
        "total": len(rows),
        "with_expected_source": len(with_source),
        "source_hits": sum(row["passed"] for row in with_source),
        "abstention_cases": len(abstentions),
        "abstention_hits": sum(row["passed"] for row in abstentions),
        "passed": sum(row["passed"] for row in rows),
        "latency_ms": {
            "min": min(latencies),
            "max": max(latencies),
            "mean": round(statistics.fmean(latencies), 2),
            "median": round(statistics.median(latencies), 2),
        },
        "cases": rows,
    }


def _source(value: str | None) -> str:
    return value or "(nenhuma)"


def render(report: dict) -> str:
    lines = [
        "OpsAtlas: avaliacao de busca",
        f"python: {report['python']}",
        f"conjunto: {report['set']}",
        f"documentos indexados: {report['documents_ready']}",
        f"modo de resposta: {report['llm_mode']}",
        f"modo de busca: {report['embedding_mode']}",
        f"ingestao: {report['ingestion_mode']}",
        "",
        f"{'id':<4} {'resultado':<10} {'ms':>8}  {'esperada':<32} obtida",
    ]
    for row in report["cases"]:
        result = "PASSOU" if row["passed"] else "FALHOU"
        lines.append(
            f"{row['id']:<4} {result:<10} {row['latency_ms']:>8.2f}  "
            f"{_source(row['expected_source']):<32} {_source(row['obtained_source'])}"
        )
    latency = report["latency_ms"]
    lines.extend(
        [
            "",
            f"acerto da fonte no primeiro trecho: {report['source_hits']}/{report['with_expected_source']}",
            f"abstencao correta: {report['abstention_hits']}/{report['abstention_cases']}",
            f"aprovados: {report['passed']}/{report['total']}",
            (
                "latencia ms (campo latency_ms): "
                f"min={latency['min']:.2f} mediana={latency['median']:.2f} "
                f"media={latency['mean']:.2f} max={latency['max']:.2f}"
            ),
        ]
    )
    return "\n".join(lines)


def main() -> None:
    report = run_set()
    print(render(report))
    print()
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
