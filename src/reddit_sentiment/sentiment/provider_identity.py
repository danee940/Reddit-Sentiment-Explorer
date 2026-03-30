from __future__ import annotations

from reddit_sentiment.core.config import Settings
from reddit_sentiment.sentiment.providers.base import (
    MOCK_PROVIDER_VERSION,
    XLM_ROBERTA_PROVIDER_VERSION,
    get_openai_provider_version,
)


def sentiment_provider_identity(settings: Settings) -> tuple[str, str]:
    if settings.sentiment_provider == "openai" and settings.llm_api_key:
        return "openai", get_openai_provider_version(settings.llm_model)
    if settings.sentiment_provider == "xlm_roberta":
        return "xlm_roberta", XLM_ROBERTA_PROVIDER_VERSION
    return "mock", MOCK_PROVIDER_VERSION
