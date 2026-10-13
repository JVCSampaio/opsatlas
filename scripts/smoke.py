"""Black-box integration smoke; works with Compose, Kubernetes or a local server."""

import argparse
import json
import time

import httpx


def run(base_url, key=""):
    headers = {"X-Tenant": "smoke"}
    if key:
        headers["Authorization"] = "Bearer " + key
    with httpx.Client(base_url=base_url, headers=headers, timeout=90) as client:
        client.get("/health/ready").raise_for_status()
        client.post("/api/demo/seed").raise_for_status()
        for _ in range(60):
            documents = client.get("/api/documents").json()
            if len(documents) == 3 and all(d["status"] == "ready" for d in documents):
                break
            time.sleep(2)
        else:
            raise RuntimeError("Documents did not become ready")
        result = client.post(
            "/api/ask", json={"question": "Atraso dos consumidores Kafka número de partições"}
        )
        result.raise_for_status()
        payload = result.json()
        assert payload["citations"][0]["source"] == "runbooks/kafka-consumer-lag"
        assert not payload["abstained"]
        unknown = client.post(
            "/api/ask", json={"question": "Intergalactic chess championship"}
        ).json()
        assert unknown["abstained"] and not unknown["citations"]
        report = client.post("/api/evaluations").json()
        assert report["passed"] == report["total"] == 4
        print(
            json.dumps(
                {
                    "status": "passed",
                    "documents": len(documents),
                    "evaluation": report,
                    "answer_mode": payload["mode"],
                    "latency_ms": payload["latency_ms"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--key", default="")
    args = parser.parse_args()
    run(args.url, args.key)
