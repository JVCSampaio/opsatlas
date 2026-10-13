import pytest


@pytest.fixture(autouse=True)
def isolate_provider_settings(monkeypatch):
    """Never let a developer's .env turn unit tests into paid model calls."""
    for name, value in {
        "INGESTION_MODE": "inline",
        "LLM_MODE": "extractive",
        "EMBEDDING_MODEL": "",
        "API_KEY": "",
        "LLM_API_KEY": "",
        "OTLP_ENDPOINT": "",
    }.items():
        monkeypatch.setenv("OPSATLAS_" + name, value)
