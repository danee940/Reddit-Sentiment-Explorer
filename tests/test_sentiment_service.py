from __future__ import annotations

import asyncio
from dataclasses import dataclass

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.sentiment.providers.base import SentimentPrediction
from reddit_sentiment.services.sentiment_service import SentimentService


@dataclass
class DocumentStub:
    id: str
    full_text: str


@dataclass
class QueryRunStub:
    id: str
    language_filter: str


class FlakyProvider:
    def __init__(self, failing_text: str) -> None:
        self.failing_text = failing_text
        self.classify_calls: list[str] = []
        self.aclose_calls = 0

    async def classify(self, text: str, content_language: str) -> SentimentPrediction:
        self.classify_calls.append(text)
        if text == self.failing_text:
            raise RuntimeError("provider exhausted retries")
        return SentimentPrediction(
            label=SentimentLabel.neutral,
            score_value=0,
            confidence=0.9,
            rationale=None,
            evidence_phrases=[],
            provider_name="openai",
            provider_version="test",
        )

    async def aclose(self) -> None:
        self.aclose_calls += 1


def _build_service(provider: FlakyProvider, concurrency: int) -> SentimentService:
    service = SentimentService.__new__(SentimentService)
    service.provider = provider
    service.provider_name = "openai"
    service.provider_version = "test"

    class SettingsStub:
        sentiment_concurrency = concurrency

    service.settings = SettingsStub()  # type: ignore[assignment]

    async def _empty_existing(query_run, document_ids):  # type: ignore[no-untyped-def]
        return {}

    async def _empty_reusable(document_ids):  # type: ignore[no-untyped-def]
        return {}

    persisted: list[str] = []

    def _persist(query_run, document, prediction):  # type: ignore[no-untyped-def]
        persisted.append(document.id)
        return prediction

    service._get_existing_results = _empty_existing  # type: ignore[assignment]
    service._get_reusable_results = _empty_reusable  # type: ignore[assignment]
    service._persist_prediction = _persist  # type: ignore[assignment]
    service.persisted = persisted  # type: ignore[attr-defined]
    return service


def test_classify_documents_skips_failed_document_and_persists_rest() -> None:
    provider = FlakyProvider(failing_text="doc-2-text")
    service = _build_service(provider, concurrency=4)
    query_run = QueryRunStub(id="run-1", language_filter="en")
    documents = [
        DocumentStub(id="doc-1", full_text="doc-1-text"),
        DocumentStub(id="doc-2", full_text="doc-2-text"),
        DocumentStub(id="doc-3", full_text="doc-3-text"),
    ]

    results = asyncio.run(service.classify_documents(query_run, documents))  # type: ignore[arg-type]

    assert service.persisted == ["doc-1", "doc-3"]  # type: ignore[attr-defined]
    assert len(results) == 2
    assert provider.aclose_calls == 1


def test_classify_documents_persists_all_when_provider_succeeds() -> None:
    provider = FlakyProvider(failing_text="never-matches")
    service = _build_service(provider, concurrency=2)
    query_run = QueryRunStub(id="run-1", language_filter="en")
    documents = [
        DocumentStub(id="doc-1", full_text="doc-1-text"),
        DocumentStub(id="doc-2", full_text="doc-2-text"),
    ]

    results = asyncio.run(service.classify_documents(query_run, documents))  # type: ignore[arg-type]

    assert service.persisted == ["doc-1", "doc-2"]  # type: ignore[attr-defined]
    assert len(results) == 2
