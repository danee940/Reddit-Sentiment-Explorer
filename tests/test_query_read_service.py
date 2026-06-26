from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from reddit_sentiment.core.enums import DocumentSourceType, SentimentLabel
from reddit_sentiment.services.query_read_service import QueryReadService


@dataclass
class QueryRunStub:
    id: str = "run-1"
    query_id: str = "q-1"
    sentiment_provider_name: str = "mock"
    sentiment_provider_version: str = "heuristic-v3"
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class QueryStub:
    id: str = "q-1"
    raw_term: str = "linux"


@dataclass
class SubredditStub:
    id: str = "sub-1"
    name: str = "linux"


@dataclass
class DocumentStub:
    id: str = "doc-1"
    source_type: DocumentSourceType = DocumentSourceType.post
    subreddit_id: str = "sub-1"
    created_utc: datetime = field(default_factory=lambda: datetime.now(UTC))
    score: int = 42
    full_text: str = "some content for the document"
    permalink: str = "https://reddit.com/r/linux/comments/abc/title/"


@dataclass
class SentimentResultStub:
    document_id: str = "doc-1"
    query_run_id: str = "run-1"
    label: SentimentLabel = SentimentLabel.positive
    score_value: int = 1
    confidence: float = 0.9
    rationale: str = "Looks positive"
    evidence_phrases: list[str] = field(default_factory=lambda: ["great feature"])


class _ScalarSession:
    def __init__(self, return_value: Any) -> None:
        self._return_value = return_value

    async def scalar(self, stmt: Any) -> Any:
        return self._return_value

    async def get(self, model: Any, pk: Any) -> Any:
        return self._return_value

    async def execute(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, rows: list) -> None:
                self._rows = rows

            def all(self) -> list:
                return self._rows

        return _Result([])


class _GetSession:
    def __init__(self, return_value: Any) -> None:
        self._return_value = return_value

    async def get(self, model: Any, pk: Any) -> Any:
        return self._return_value

    async def scalar(self, stmt: Any) -> Any:
        return None


class _ExecuteSession:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    async def execute(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, rows: list) -> None:
                self._rows = rows

            def all(self) -> list:
                return self._rows

        return _Result(self._rows)

    async def scalar(self, stmt: Any) -> Any:
        return None

    async def get(self, model: Any, pk: Any) -> Any:
        return None


def test_query_read_service_init_sets_session() -> None:
    class SessionStub:
        pass

    session = SessionStub()
    service = QueryReadService(session=session)  # type: ignore[arg-type]
    assert service.session is session


def test_get_latest_run_for_provider_returns_run_when_found() -> None:
    run = QueryRunStub()
    session = _ScalarSession(return_value=run)
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(
        service.get_latest_run_for_provider("q-1", "mock", "heuristic-v3")
    )
    assert result is run


def test_get_latest_run_for_provider_returns_none_when_not_found() -> None:
    session = _ScalarSession(return_value=None)
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(
        service.get_latest_run_for_provider("q-1", "mock", "heuristic-v3")
    )
    assert result is None


def test_get_run_returns_run_when_found() -> None:
    run = QueryRunStub()
    session = _GetSession(return_value=run)
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_run("run-1"))
    assert result is run


def test_get_run_returns_none_when_not_found() -> None:
    session = _GetSession(return_value=None)
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_run("missing"))
    assert result is None


def test_get_query_returns_query_when_found() -> None:
    query = QueryStub()
    session = _GetSession(return_value=query)
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_query("q-1"))
    assert result is query


def test_get_query_returns_none_when_not_found() -> None:
    session = _GetSession(return_value=None)
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_query("missing"))
    assert result is None


def test_get_run_documents_returns_empty_list_when_no_rows() -> None:
    session = _ExecuteSession(rows=[])
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_run_documents("run-1"))
    assert result == []


def test_get_run_documents_maps_rows_with_sentiment() -> None:
    doc = DocumentStub()
    sentiment = SentimentResultStub()
    subreddit = SubredditStub()

    session = _ExecuteSession(rows=[(doc, sentiment, subreddit)])
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    results = asyncio.run(service.get_run_documents("run-1"))

    assert len(results) == 1
    result = results[0]
    assert result.document_id == "doc-1"
    assert result.subreddit == "linux"
    assert result.score == 42
    assert result.sentiment_label == SentimentLabel.positive
    assert result.sentiment_score == 1
    assert result.sentiment_confidence == 0.9
    assert result.sentiment_evidence_phrases == ["great feature"]


def test_get_run_documents_maps_rows_without_sentiment() -> None:
    doc = DocumentStub()
    subreddit = SubredditStub()

    session = _ExecuteSession(rows=[(doc, None, subreddit)])
    service = QueryReadService(session=session)  # type: ignore[arg-type]

    results = asyncio.run(service.get_run_documents("run-1"))

    assert len(results) == 1
    result = results[0]
    assert result.sentiment_label is None
    assert result.sentiment_score is None
    assert result.sentiment_confidence is None
    assert result.sentiment_evidence_phrases == []
