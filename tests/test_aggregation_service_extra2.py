from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from reddit_sentiment.core.enums import AggregateType, DocumentSourceType, SentimentLabel
from reddit_sentiment.services.aggregation_service import AggregationService


@dataclass
class SubredditStub:
    id: str = "sub-1"
    name: str = "linux"


@dataclass
class DocumentStub:
    id: str = "doc-1"
    source_type: DocumentSourceType = DocumentSourceType.post
    subreddit_id: str = "sub-1"
    created_utc: datetime = field(default_factory=lambda: datetime(2025, 1, 15, 12, 0, tzinfo=UTC))
    score: int = 10
    full_text: str = "this is a great linux kernel release"
    permalink: str | None = None


@dataclass
class SentimentResultStub:
    document_id: str = "doc-1"
    query_run_id: str = "run-1"
    label: SentimentLabel = SentimentLabel.positive
    score_value: int = 1
    confidence: float = 0.85
    rationale: str | None = "looks good"
    evidence_phrases: list[str] = field(default_factory=lambda: ["great linux"])


@dataclass
class QueryDocumentMatchStub:
    query_run_id: str = "run-1"
    document_id: str = "doc-1"


@dataclass
class AggregateStub:
    query_run_id: str = "run-1"
    aggregate_type: AggregateType = AggregateType.overview
    payload: dict = field(default_factory=lambda: {"total_documents": 5})


class _BuildSession:
    def __init__(self, rows: list, query_context_row: Any) -> None:
        self._rows = rows
        self._query_context_row = query_context_row
        self.added: list[Any] = []
        self.deleted: list[Any] = []
        self.flush_calls = 0
        self._execute_calls = 0

    async def execute(self, stmt: Any) -> Any:
        self._execute_calls += 1

        class _Result:
            def __init__(self, rows: list, single: Any = None) -> None:
                self._rows = rows
                self._single = single

            def all(self) -> list:
                return self._rows

            def one_or_none(self) -> Any:
                return self._single

        if self._execute_calls == 1:
            return _Result([], single=self._query_context_row)
        if self._execute_calls == 2:
            return _Result(self._rows)
        return _Result([], single=None)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flush_calls += 1


class _GetPayloadSession:
    def __init__(self, aggregates: list) -> None:
        self._aggregates = aggregates

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, items: list) -> None:
                self._items = items

            def all(self) -> list:
                return self._items

        return _Result(self._aggregates)


class _ReplaceAggregatesSession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.added: list[Any] = []
        self.flush_calls = 0

    async def execute(self, stmt: Any) -> Any:
        self.execute_calls += 1
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flush_calls += 1


class _QueryContextSession:
    def __init__(self, context_row: Any) -> None:
        self._context_row = context_row

    async def execute(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, row: Any) -> None:
                self._row = row

            def one_or_none(self) -> Any:
                return self._row

        return _Result(self._context_row)


def test_get_query_context_with_valid_row() -> None:
    context_row = ("linux kernel", "en")
    session = _QueryContextSession(context_row)
    service = AggregationService(session=session)  # type: ignore[arg-type]

    excluded_terms, stop_words = asyncio.run(service._get_query_context("run-1"))

    assert isinstance(excluded_terms, set)
    assert isinstance(stop_words, set)
    assert "linux" in excluded_terms
    assert "kernel" in excluded_terms


def test_get_query_context_with_no_row() -> None:
    session = _QueryContextSession(None)
    service = AggregationService(session=session)  # type: ignore[arg-type]

    excluded_terms, stop_words = asyncio.run(service._get_query_context("run-1"))

    assert isinstance(excluded_terms, set)
    assert isinstance(stop_words, set)


def test_replace_aggregates_calls_delete_add_flush() -> None:
    session = _ReplaceAggregatesSession()
    service = AggregationService(session=session)  # type: ignore[arg-type]

    payload = {
        "overview": {"total_documents": 3},
        "sentiment_distribution": [],
        "sentiment_timeline": [],
        "volume_timeline": [],
        "subreddit_breakdown": [],
        "sentiment_heatmap": [],
        "rolling_sentiment_timeline": [],
        "phrase_breakdown": [],
        "spike_events": [],
    }

    asyncio.run(service._replace_aggregates("run-1", payload))

    assert session.execute_calls == 1
    aggregate_types = {type(obj).__name__ for obj in session.added}
    assert "Aggregate" in aggregate_types
    assert session.flush_calls == 1


def test_get_payload_returns_stored_values() -> None:
    agg = AggregateStub(aggregate_type=AggregateType.overview, payload={"total_documents": 5})
    session = _GetPayloadSession(aggregates=[agg])
    service = AggregationService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_payload("run-1"))

    assert "overview" in result
    assert result["overview"] == {"total_documents": 5}
    assert "sentiment_distribution" in result


def test_get_payload_uses_empty_defaults_for_missing_aggregates() -> None:
    session = _GetPayloadSession(aggregates=[])
    service = AggregationService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_payload("run-1"))

    assert result["overview"] == {}
    assert result["sentiment_distribution"] == []


def test_build_returns_payload_with_correct_structure() -> None:
    doc = DocumentStub()
    sentiment = SentimentResultStub()
    subreddit = SubredditStub()
    match = QueryDocumentMatchStub()

    query_context_row = ("linux", "en")

    class _FullBuildSession:
        def __init__(self) -> None:
            self._execute_calls = 0
            self.added: list[Any] = []
            self.flush_calls = 0

        async def execute(self, stmt: Any) -> Any:
            self._execute_calls += 1

            class _Result:
                def __init__(self, rows: list, single: Any = None) -> None:
                    self._rows = rows
                    self._single = single

                def all(self) -> list:
                    return self._rows

                def one_or_none(self) -> Any:
                    return self._single

            if self._execute_calls == 1:
                return _Result([], single=query_context_row)
            if self._execute_calls == 2:
                return _Result([(match, doc, sentiment, subreddit)])
            return _Result([], single=None)

        def add(self, obj: Any) -> None:
            self.added.append(obj)

        async def flush(self) -> None:
            self.flush_calls += 1

    session = _FullBuildSession()
    service = AggregationService(session=session)  # type: ignore[arg-type]

    payload = asyncio.run(service.build("run-1"))

    assert "overview" in payload
    assert payload["overview"]["total_documents"] == 1
    assert "sentiment_distribution" in payload
    assert "sentiment_timeline" in payload
    assert session.flush_calls == 1


def test_extract_evidence_terms_skips_empty_token_phrases() -> None:
    service = AggregationService(None)  # type: ignore[arg-type]

    phrases = [
        "a",
        "good performance under load",
        "fast",
    ]
    excluded: set[str] = set()
    stop_words: set[str] = {"a"}

    result = service._extract_evidence_terms(phrases, excluded, stop_words)

    assert "good performance under load" in result or len(result) > 0
    assert not any(p == "a" for p in result)


def test_extract_evidence_terms_stops_at_five_phrases() -> None:
    service = AggregationService(None)  # type: ignore[arg-type]

    phrases = [
        "first phrase here",
        "second phrase here",
        "third phrase here",
        "fourth phrase here",
        "fifth phrase here",
        "sixth phrase here",
    ]
    excluded: set[str] = set()
    stop_words: set[str] = set()

    result = service._extract_evidence_terms(phrases, excluded, stop_words)

    assert len(result) == 5
