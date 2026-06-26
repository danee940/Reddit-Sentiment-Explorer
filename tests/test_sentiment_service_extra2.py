from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.sentiment.providers.base import (
    MOCK_PROVIDER_VERSION,
    SentimentPrediction,
)
from reddit_sentiment.services.sentiment_service import SentimentService


@dataclass
class DocumentStub:
    id: str
    full_text: str


@dataclass
class QueryRunStub:
    id: str
    language_filter: str = "en"


@dataclass
class SentimentResultStub:
    document_id: str = "doc-1"
    query_run_id: str = "run-1"
    provider_name: str = "mock"
    provider_version: str = MOCK_PROVIDER_VERSION
    label: SentimentLabel = SentimentLabel.positive
    score_value: int = 1
    confidence: float = 0.85
    rationale: str | None = "looks good"
    evidence_phrases: list[str] = field(default_factory=list)


class _ExistingResultSession:
    def __init__(self, existing: Any) -> None:
        self._existing = existing
        self.added: list[Any] = []

    async def scalar(self, stmt: Any) -> Any:
        return self._existing

    def add(self, obj: Any) -> None:
        self.added.append(obj)


class _ReusableResultSession:
    def __init__(self, reusable: Any) -> None:
        self._scalar_calls = 0
        self._reusable = reusable
        self.added: list[Any] = []

    async def scalar(self, stmt: Any) -> Any:
        self._scalar_calls += 1
        if self._scalar_calls == 1:
            return None
        return self._reusable

    def add(self, obj: Any) -> None:
        self.added.append(obj)


class _NewClassificationSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    async def scalar(self, stmt: Any) -> None:
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)


class _SuccessProvider:
    async def classify(self, text: str, content_language: str) -> SentimentPrediction:
        return SentimentPrediction(
            label=SentimentLabel.neutral,
            score_value=0,
            confidence=0.9,
            rationale=None,
            evidence_phrases=[],
            provider_name="mock",
            provider_version=MOCK_PROVIDER_VERSION,
        )

    async def aclose(self) -> None:
        pass


def _make_service(session: Any) -> SentimentService:
    service = SentimentService.__new__(SentimentService)
    service.provider = _SuccessProvider()
    service.provider_name = "mock"
    service.provider_version = MOCK_PROVIDER_VERSION
    service._owned_provider = True
    service.session = session

    class SettingsStub:
        sentiment_confidence_threshold = 0.6

    service.settings = SettingsStub()  # type: ignore[assignment]
    return service


def test_classify_document_returns_existing_result_without_calling_provider() -> None:
    existing = SentimentResultStub(document_id="doc-1", query_run_id="run-1")
    session = _ExistingResultSession(existing=existing)
    service = _make_service(session)

    query_run = QueryRunStub(id="run-1")
    document = DocumentStub(id="doc-1", full_text="some text")

    result = asyncio.run(service.classify_document(query_run, document))  # type: ignore[arg-type]

    assert result is existing
    assert session.added == []


def test_classify_document_uses_reusable_result_when_no_existing() -> None:
    reusable = SentimentResultStub(document_id="doc-1", query_run_id="run-other")
    session = _ReusableResultSession(reusable=reusable)
    service = _make_service(session)

    query_run = QueryRunStub(id="run-1")
    document = DocumentStub(id="doc-1", full_text="some text")

    asyncio.run(service.classify_document(query_run, document))  # type: ignore[arg-type]

    assert len(session.added) == 1
    persisted = session.added[0]
    assert persisted.document_id == "doc-1"
    assert persisted.query_run_id == "run-1"
    assert persisted.label == SentimentLabel.positive


def test_classify_document_calls_provider_when_no_cached_result() -> None:
    session = _NewClassificationSession()
    service = _make_service(session)

    query_run = QueryRunStub(id="run-1")
    document = DocumentStub(id="doc-1", full_text="some new text")

    result = asyncio.run(service.classify_document(query_run, document))  # type: ignore[arg-type]

    assert len(session.added) == 1
    assert result.label == SentimentLabel.neutral


class _ExistingBatchSession:
    def __init__(self, existing_result: Any) -> None:
        self._existing = existing_result
        self.added: list[Any] = []

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, items: list) -> None:
                self._items = items

            def __iter__(self):  # type: ignore[no-untyped-def]
                return iter(self._items)

        return _Result([self._existing])

    def add(self, obj: Any) -> None:
        self.added.append(obj)


def test_classify_documents_uses_existing_results() -> None:
    existing = SentimentResultStub(document_id="doc-1", query_run_id="run-1")
    session = _ExistingBatchSession(existing_result=existing)
    service = SentimentService.__new__(SentimentService)
    service.provider = _SuccessProvider()
    service.provider_name = "mock"
    service.provider_version = MOCK_PROVIDER_VERSION
    service._owned_provider = True
    service.session = session  # type: ignore[assignment]

    class SettingsStub:
        sentiment_concurrency = 4
        sentiment_confidence_threshold = 0.6

    service.settings = SettingsStub()  # type: ignore[assignment]

    async def fake_get_reusable_results(document_ids: list[str]) -> dict:
        return {}

    service._get_reusable_results = fake_get_reusable_results  # type: ignore[assignment]

    query_run = QueryRunStub(id="run-1")
    documents = [DocumentStub(id="doc-1", full_text="some text")]

    results = asyncio.run(service.classify_documents(query_run, documents))  # type: ignore[arg-type]

    assert len(results) == 1
    assert results[0] is existing
    assert session.added == []


class _ReusableBatchSession:
    def __init__(self, reusable: Any) -> None:
        self._reusable = reusable
        self.added: list[Any] = []
        self._call_count = 0

    async def scalars(self, stmt: Any) -> Any:
        self._call_count += 1

        class _EmptyResult:
            def __iter__(self):  # type: ignore[no-untyped-def]
                return iter([])

        class _ReusableResult:
            def __init__(self, item: Any) -> None:
                self._item = item

            def __iter__(self):  # type: ignore[no-untyped-def]
                return iter([self._item])

        if self._call_count == 1:
            return _EmptyResult()
        return _ReusableResult(self._reusable)

    def add(self, obj: Any) -> None:
        self.added.append(obj)


def test_classify_documents_uses_reusable_results() -> None:
    reusable = SentimentResultStub(document_id="doc-1", query_run_id="run-other")
    session = _ReusableBatchSession(reusable=reusable)
    service = SentimentService.__new__(SentimentService)
    service.provider = _SuccessProvider()
    service.provider_name = "mock"
    service.provider_version = MOCK_PROVIDER_VERSION
    service._owned_provider = True
    service.session = session  # type: ignore[assignment]

    class SettingsStub:
        sentiment_concurrency = 4
        sentiment_confidence_threshold = 0.6

    service.settings = SettingsStub()  # type: ignore[assignment]

    query_run = QueryRunStub(id="run-1")
    documents = [DocumentStub(id="doc-1", full_text="some text")]

    results = asyncio.run(service.classify_documents(query_run, documents))  # type: ignore[arg-type]

    assert len(results) == 1
    assert len(session.added) == 1
    assert session.added[0].query_run_id == "run-1"


class _EmptyScalarsSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    async def scalars(self, stmt: Any) -> Any:
        class _EmptyResult:
            def __iter__(self):  # type: ignore[no-untyped-def]
                return iter([])

        return _EmptyResult()

    def add(self, obj: Any) -> None:
        self.added.append(obj)


def test_get_existing_results_returns_empty_dict_for_empty_document_ids() -> None:
    session = _EmptyScalarsSession()
    service = _make_service(session)

    query_run = QueryRunStub(id="run-1")
    result = asyncio.run(service._get_existing_results(query_run, []))  # type: ignore[arg-type]

    assert result == {}


def test_get_reusable_results_returns_empty_dict_for_empty_document_ids() -> None:
    session = _EmptyScalarsSession()
    service = _make_service(session)

    result = asyncio.run(service._get_reusable_results([]))

    assert result == {}


def test_persist_prediction_adds_result_to_session() -> None:
    session = _NewClassificationSession()
    service = _make_service(session)

    query_run = QueryRunStub(id="run-1")
    document = DocumentStub(id="doc-1", full_text="good product, great quality")
    prediction = SentimentPrediction(
        label=SentimentLabel.positive,
        score_value=1,
        confidence=0.9,
        rationale="Positive sentiment",
        evidence_phrases=["great quality"],
        provider_name="mock",
        provider_version=MOCK_PROVIDER_VERSION,
    )

    result = service._persist_prediction(query_run, document, prediction)  # type: ignore[arg-type]

    assert len(session.added) == 1
    assert result.document_id == "doc-1"
    assert result.query_run_id == "run-1"
    assert result.label == SentimentLabel.positive
    assert session.added[0] is result
