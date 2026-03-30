from __future__ import annotations

import asyncio
import logging
from typing import Any

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.sentiment.providers.base import (
    XLM_ROBERTA_PROVIDER_VERSION,
    SentimentPrediction,
)

logger = logging.getLogger(__name__)

_MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual"
_STRONG_THRESHOLD = 0.85
_MAX_TOKENS = 512

_LABEL_MAP: dict[str, SentimentLabel] = {
    "positive": SentimentLabel.positive,
    "neutral": SentimentLabel.neutral,
    "negative": SentimentLabel.negative,
}

_STRONG_LABEL_MAP: dict[str, SentimentLabel] = {
    "positive": SentimentLabel.very_positive,
    "negative": SentimentLabel.very_negative,
}

_SCORE_MAP: dict[SentimentLabel, int] = {
    SentimentLabel.very_negative: -2,
    SentimentLabel.negative: -1,
    SentimentLabel.neutral: 0,
    SentimentLabel.positive: 1,
    SentimentLabel.very_positive: 2,
}


class XLMRobertaSentimentProvider:
    def __init__(self) -> None:
        self._pipeline: Any = None

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            try:
                from transformers import pipeline as hf_pipeline  # type: ignore[import-untyped]
            except ImportError as exc:
                raise ImportError(
                    "transformers and torch are required for the xlm_roberta provider. "
                    "Install them with: pip install 'reddit-sentiment[ml]'"
                ) from exc
            logger.info("Loading XLM-RoBERTa sentiment model: %s", _MODEL_NAME)
            self._pipeline = hf_pipeline(
                "text-classification",
                model=_MODEL_NAME,
                top_k=None,
                truncation=True,
                max_length=_MAX_TOKENS,
            )
        return self._pipeline

    def _classify_sync(self, text: str) -> SentimentPrediction:
        pipe = self._get_pipeline()
        results: list[dict[str, Any]] = pipe(text[:_MAX_TOKENS])[0]
        top = results[0]
        top_label_raw = top["label"].lower()
        top_score = float(top["score"])

        if (
            top_label_raw in _STRONG_LABEL_MAP
            and top_score > _STRONG_THRESHOLD
        ):
            label = _STRONG_LABEL_MAP[top_label_raw]
        else:
            label = _LABEL_MAP.get(top_label_raw, SentimentLabel.neutral)

        return SentimentPrediction(
            label=label,
            score_value=_SCORE_MAP[label],
            confidence=round(top_score, 4),
            rationale=None,
            evidence_phrases=[],
            provider_name="xlm_roberta",
            provider_version=XLM_ROBERTA_PROVIDER_VERSION,
        )

    async def classify(
        self, text: str, content_language: str
    ) -> SentimentPrediction:
        return await asyncio.to_thread(self._classify_sync, text)
