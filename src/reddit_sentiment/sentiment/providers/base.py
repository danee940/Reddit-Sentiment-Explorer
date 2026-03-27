from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from reddit_sentiment.core.enums import SentimentLabel

MOCK_PROVIDER_VERSION = "heuristic-v3"
OPENAI_PROVIDER_OUTPUT_VERSION = "localized-rationale-v1"


@dataclass(slots=True)
class SentimentPrediction:
    label: SentimentLabel
    score_value: int
    confidence: float | None
    rationale: str | None
    evidence_phrases: list[str]
    provider_name: str
    provider_version: str


class SentimentProvider(Protocol):
    async def classify(self, text: str, content_language: str) -> SentimentPrediction:
        ...


def get_openai_provider_version(model: str) -> str:
    return f"{model}:{OPENAI_PROVIDER_OUTPUT_VERSION}"
