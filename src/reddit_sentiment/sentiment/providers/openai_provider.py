from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from reddit_sentiment.core.config import Settings, get_settings
from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.core.languages import get_language_label, normalize_content_language
from reddit_sentiment.sentiment.providers.base import (
    SentimentPrediction,
    get_openai_provider_version,
)

logger = logging.getLogger(__name__)


class OpenAISentimentProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client_factory = client_factory or httpx.AsyncClient

    @staticmethod
    def _normalize_confidence(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized_value = value.strip().lower()
            if not normalized_value:
                return None
            named_confidence_values = {
                "very_low": 0.1,
                "low": 0.3,
                "medium": 0.5,
                "moderate": 0.5,
                "high": 0.8,
                "very_high": 0.95,
            }
            if normalized_value in named_confidence_values:
                return named_confidence_values[normalized_value]
            return float(normalized_value)
        return None

    async def classify(self, text: str, content_language: str) -> SentimentPrediction:
        language_code = normalize_content_language(content_language)
        language_label = get_language_label(language_code)
        prompt = (
            "You are classifying the sentiment of a single Reddit text written in "
            f"{language_label} ({language_code}). "
            "Return only one valid JSON object with exactly these keys: "
            "label, score_value, confidence, rationale, evidence_phrases. "
            "Do not wrap the JSON in markdown. Do not add explanations before or after the JSON. "
            "Rules: "
            "label must be exactly one of very_negative, negative, neutral, "
            "positive, very_positive. "
            "score_value must be exactly one of -2, -1, 0, 1, 2. "
            "confidence must be a JSON number between 0 and 1, not a string "
            "and not a word like high or medium. "
            "rationale must be a short explanation in the same language as the input text. "
            "evidence_phrases must be a JSON array containing 1 to 3 short "
            "exact quotes copied from the input text. "
            "Do not paraphrase evidence_phrases. Do not invent text that is "
            "not present in the input. "
            "Base the classification only on the provided text."
        )
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        data = await self._post_completion(headers, payload)
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        usage = data.get("usage") or {}
        if usage:
            logger.info(
                "sentiment_provider_usage provider=openai "
                "model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                self.settings.llm_model,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
            )
        label = SentimentLabel(parsed["label"])
        raw_evidence_phrases = parsed.get("evidence_phrases", [])
        if not isinstance(raw_evidence_phrases, list):
            raw_evidence_phrases = []
        return SentimentPrediction(
            label=label,
            score_value=int(parsed["score_value"]),
            confidence=self._normalize_confidence(parsed.get("confidence")),
            rationale=parsed.get("rationale"),
            evidence_phrases=[
                str(item).strip() for item in raw_evidence_phrases if str(item).strip()
            ][:3],
            provider_name="openai",
            provider_version=get_openai_provider_version(self.settings.llm_model),
        )

    @retry(
        reraise=True,
        retry=retry_if_exception_type((httpx.HTTPError, ValueError, json.JSONDecodeError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
    )
    async def _post_completion(self, headers: dict[str, str], payload: dict) -> dict:
        async with self.client_factory(
            base_url=self.settings.llm_api_base_url,
            timeout=60.0,
        ) as client:
            response = await client.post("/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())
