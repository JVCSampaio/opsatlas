"""Run browser tests against a fresh disposable database on every invocation."""

import os
import tempfile
from pathlib import Path

import uvicorn

if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="opsatlas-e2e-") as folder:
        os.environ["OPSATLAS_DATABASE_URL"] = "sqlite:///" + (Path(folder) / "demo.db").as_posix()
        os.environ["OPSATLAS_INGESTION_MODE"] = "inline"
        os.environ["OPSATLAS_LLM_MODE"] = "extractive"
        os.environ["OPSATLAS_EMBEDDING_MODEL"] = ""
        os.environ["OPSATLAS_API_KEY"] = ""
        os.environ["OPSATLAS_OTLP_ENDPOINT"] = ""
        uvicorn.run("opsatlas.api:create_app", factory=True, host="127.0.0.1", port=8000)
