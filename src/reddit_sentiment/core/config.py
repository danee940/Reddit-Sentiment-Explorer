from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8050
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment"
    arctic_shift_base_url: str = "https://arctic-shift.photon-reddit.com/api"
    arctic_shift_request_limit: int | Literal["auto"] = 25
    arctic_shift_comment_limit: int | Literal["auto"] = 100
    arctic_shift_concurrency: int = 8
    sentiment_provider: str = "mock"
    llm_api_key: str = ""
    llm_api_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_retry_attempts: int = 3
    sentiment_confidence_threshold: float = 0.6
    sentiment_concurrency: int = 8
    query_cache_ttl_hours: int = 12
    query_run_stale_after_minutes: int = 30
    default_subreddits: list[str] = Field(
        default_factory=lambda: ["hungary", "askhungary", "budapest", "hu"]
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def strip_llm_api_key(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("default_subreddits", mode="before")
    @classmethod
    def split_csv_values(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("arctic_shift_request_limit", "arctic_shift_comment_limit", mode="before")
    @classmethod
    def normalize_arctic_shift_limit(cls, value: int | str) -> int | Literal["auto"]:
        if isinstance(value, str):
            normalized_value = value.strip().lower()
            if normalized_value == "auto":
                return "auto"
        return int(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
