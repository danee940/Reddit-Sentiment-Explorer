from __future__ import annotations

from typing import cast

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.config import Settings, get_settings
from reddit_sentiment.core.languages import normalize_content_language
from reddit_sentiment.db.models import Document, QueryRun, SentimentResult
from reddit_sentiment.sentiment.providers import MockSentimentProvider, OpenAISentimentProvider
from reddit_sentiment.sentiment.providers.base import (
    MOCK_PROVIDER_VERSION,
    SentimentProvider,
    get_openai_provider_version,
)


class SentimentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        provider: SentimentProvider | None = None,
        provider_name: str | None = None,
        provider_version: str | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        if provider is not None:
            self.provider = provider
        elif self.settings.llm_provider == "openai" and self.settings.llm_api_key:
            self.provider = OpenAISentimentProvider(self.settings)
        else:
            self.provider = MockSentimentProvider()
        self.provider_name = provider_name or self._get_provider_name()
        self.provider_version = provider_version or self._get_provider_version(self.provider_name)

    async def classify_document(self, query_run: QueryRun, document: Document) -> SentimentResult:
        existing_result = await self.session.scalar(
            select(SentimentResult)
            .where(SentimentResult.query_run_id == query_run.id)
            .where(SentimentResult.document_id == document.id)
        )
        if existing_result is not None:
            return existing_result

        reusable_result = await self._get_reusable_result(document)
        if reusable_result is not None:
            result = SentimentResult(
                query_run_id=query_run.id,
                document_id=document.id,
                provider_name=reusable_result.provider_name,
                provider_version=reusable_result.provider_version,
                label=reusable_result.label,
                score_value=reusable_result.score_value,
                confidence=reusable_result.confidence,
                rationale=reusable_result.rationale,
                evidence_phrases=reusable_result.evidence_phrases,
            )
            self.session.add(result)
            await self.session.flush()
            return result

        prediction = await self.provider.classify(document.full_text, query_run.language_filter)
        result = SentimentResult(
            query_run_id=query_run.id,
            document_id=document.id,
            provider_name=prediction.provider_name,
            provider_version=prediction.provider_version,
            label=prediction.label,
            score_value=prediction.score_value,
            confidence=prediction.confidence,
            rationale=self._normalize_rationale(
                prediction.rationale,
                prediction.confidence,
                query_run.language_filter,
            ),
            evidence_phrases=self._normalize_evidence_phrases(
                prediction.evidence_phrases,
                document.full_text,
            ),
        )
        self.session.add(result)
        await self.session.flush()
        return result

    async def _get_reusable_result(self, document: Document) -> SentimentResult | None:
        return cast(
            SentimentResult | None,
            await self.session.scalar(
                select(SentimentResult)
                .where(SentimentResult.document_id == document.id)
                .where(SentimentResult.provider_name == self.provider_name)
                .where(SentimentResult.provider_version == self.provider_version)
                .order_by(desc(SentimentResult.created_at))
            ),
        )

    def _get_provider_name(self) -> str:
        if self.settings.llm_provider == "openai" and self.settings.llm_api_key:
            return "openai"
        return "mock"

    def _get_provider_version(self, provider_name: str) -> str:
        if provider_name == "openai":
            return get_openai_provider_version(self.settings.llm_model)
        return MOCK_PROVIDER_VERSION

    def _normalize_rationale(
        self,
        rationale: str | None,
        confidence: float | None,
        content_language: str,
    ) -> str | None:
        if confidence is None or confidence >= self.settings.sentiment_confidence_threshold:
            return rationale
        detail_prefix = self._get_low_confidence_prefix(content_language)
        if detail_prefix is None:
            return rationale
        detail = f"{detail_prefix} ({confidence:.2f})."
        if rationale:
            return f"{detail} {rationale}"
        return detail

    def _get_low_confidence_prefix(self, content_language: str) -> str | None:
        language_code = normalize_content_language(content_language)
        return {
            "en": "Low-confidence result",
            "hu": "Alacsony bizonyosságú eredmény",
            "ru": "Результат с низкой уверенностью",
        }.get(language_code)

    def _normalize_evidence_phrases(self, phrases: list[str], text: str) -> list[str]:
        normalized_phrases: list[str] = []
        normalized_text = text.casefold()
        for phrase in phrases:
            cleaned_phrase = " ".join(phrase.strip().split())
            if len(cleaned_phrase) < 3:
                continue
            if cleaned_phrase.casefold() not in normalized_text:
                continue
            if cleaned_phrase not in normalized_phrases:
                normalized_phrases.append(cleaned_phrase)
            if len(normalized_phrases) == 3:
                break
        return normalized_phrases
