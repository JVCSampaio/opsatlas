"""Verify real Prometheus scrape and provisioned Grafana dashboard in Compose."""

import time

import httpx


def run():
    with httpx.Client(timeout=15) as client:
        for _ in range(30):
            result = client.get(
                "http://127.0.0.1:9090/api/v1/query", params={"query": 'up{job="opsatlas"}'}
            ).json()
            rows = result.get("data", {}).get("result", [])
            if rows and rows[0]["value"][1] == "1":
                break
            time.sleep(2)
        else:
            raise AssertionError("Prometheus did not scrape the API")
        dashboard = client.get(
            "http://127.0.0.1:3000/api/dashboards/uid/opsatlas",
            auth=("admin", "local-observability"),
        )
        dashboard.raise_for_status()
        assert len(dashboard.json()["dashboard"]["panels"]) == 4
        print("Prometheus API scrape and four-panel Grafana dashboard verified")


if __name__ == "__main__":
    run()
