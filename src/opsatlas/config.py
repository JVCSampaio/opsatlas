from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPSATLAS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./opsatlas.db"
    api_key: str = ""
    ingestion_mode: Literal["inline", "kafka"] = "inline"
    llm_mode: Literal["extractive", "llm"] = "extractive"
    llm_base_url: str = "http://127.0.0.1:8081/v1"
    llm_model: str = "local-model"
    llm_api_key: str = ""
    embedding_model: str = ""
    kafka_bootstrap: str = "kafka:9092"
    mongo_url: str = ""
    otlp_endpoint: str = ""
    max_context_chars: int = Field(default=6000, ge=500, le=32000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
