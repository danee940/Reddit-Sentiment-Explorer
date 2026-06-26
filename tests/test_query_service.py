from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from reddit_sentiment.core.config import Settings
from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.services.query_service import QueryService, normalize_term

# ---------------------------------------------------------------------------
# normalize_term
# ---------------------------------------------------------------------------


def test_normalize_term_lowercases_and_collapses_whitespace() -> None:
    assert normalize_term("  Big  Mac  ") == "big mac"


def test_normalize_term_already_normalized() -> None:
    assert normalize_term("linux") == "linux"


# ---------------------------------------------------------------------------
# Minimal in-memory session stub
# ---------------------------------------------------------------------------


@dataclass
class QueryStub:
    id: str = "q-1"
    raw_term: str = "linux"
    normalized_term: str = "linux"


@dataclass
class QueryRunStub:
    id: str = "run-1"
    query_id: str = "q-1"
    status: QueryRunStatus = QueryRunStatus.pending
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    data_fresh_until: datetime | None = None
    scope_config: dict = field(default_factory=dict)
    match_strategy: str = "phrase_then_tokens"
    language_filter: str = "en"
    sentiment_provider_name: str = "mock"
    sentiment_provider_version: str = "heuristic-v3"


class SessionStub:
    def __init__(self, scalar_return: Any = None, get_return: Any = None) -> None:
        self._scalar_return = scalar_return
        self._get_return = get_return
        self.added: list[Any] = []
        self.flush_calls = 0

    async def scalar(self, stmt: Any) -> Any:
        return self._scalar_return

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, items: list) -> None:
                self._items = items

            def all(self) -> list:
                return self._items

        return _Result([] if self._scalar_return is None else [self._scalar_return])

    async def get(self, model: Any, pk: Any) -> Any:
        return self._get_return

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flush_calls += 1

    async def begin_nested(self) -> _NestedTransaction:
        return _NestedTransaction()


class _NestedTransaction:
    async def rollback(self) -> None:
        pass

    async def commit(self) -> None:
        pass


# ---------------------------------------------------------------------------
# mark_running
# ---------------------------------------------------------------------------


def test_mark_running_sets_status_and_clears_error() -> None:
    run = QueryRunStub(status=QueryRunStatus.pending, error_message="old error")
    session = SessionStub()
    service = QueryService(session=session)  # type: ignore[arg-type]

    before = datetime.now(UTC)
    result = asyncio.run(service.mark_running(run))  # type: ignore[arg-type]
    after = datetime.now(UTC)

    assert result.status == QueryRunStatus.running
    assert result.error_message is None
    assert result.finished_at is None
    assert before <= result.started_at <= after
    assert session.flush_calls == 1


# ---------------------------------------------------------------------------
# mark_completed
# ---------------------------------------------------------------------------


def test_mark_completed_sets_status_and_fresh_until() -> None:
    run = QueryRunStub(status=QueryRunStatus.running)
    settings = Settings(query_cache_ttl_hours=6)
    session = SessionStub()
    service = QueryService(session=session, settings=settings)  # type: ignore[arg-type]

    before = datetime.now(UTC)
    result = asyncio.run(service.mark_completed(run))  # type: ignore[arg-type]
    after = datetime.now(UTC)

    assert result.status == QueryRunStatus.completed
    assert result.finished_at is not None
    assert before <= result.finished_at <= after
    assert result.data_fresh_until is not None
    expected_min = before + timedelta(hours=6)
    expected_max = after + timedelta(hours=6)
    assert expected_min <= result.data_fresh_until <= expected_max


# ---------------------------------------------------------------------------
# mark_failed
# ---------------------------------------------------------------------------


def test_mark_failed_sets_status_and_message() -> None:
    run = QueryRunStub(status=QueryRunStatus.running)
    session = SessionStub()
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.mark_failed(run, "boom"))  # type: ignore[arg-type]

    assert result.status == QueryRunStatus.failed
    assert result.error_message == "boom"
    assert result.finished_at is not None


# ---------------------------------------------------------------------------
# get_run
# ---------------------------------------------------------------------------


def test_get_run_returns_session_get_result() -> None:
    run = QueryRunStub()
    session = SessionStub(get_return=run)
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_run("run-1"))

    assert result is run


def test_get_run_returns_none_when_not_found() -> None:
    session = SessionStub(get_return=None)
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_run("missing"))

    assert result is None


# ---------------------------------------------------------------------------
# get_or_create_query — existing query path
# ---------------------------------------------------------------------------


def test_get_or_create_query_returns_existing_when_found() -> None:
    existing = QueryStub(normalized_term="linux")
    session = SessionStub(scalar_return=existing)
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_or_create_query("Linux"))

    assert result is existing
    assert session.added == []


# ---------------------------------------------------------------------------
# get_or_create_query — new query path
# ---------------------------------------------------------------------------


def test_get_or_create_query_creates_new_when_not_found() -> None:
    session = SessionStub(scalar_return=None)
    service = QueryService(session=session)  # type: ignore[arg-type]

    asyncio.run(service.get_or_create_query("Linux"))

    assert len(session.added) == 1
    added = session.added[0]
    assert added.raw_term == "Linux"
    assert added.normalized_term == "linux"


# ---------------------------------------------------------------------------
# create_run
# ---------------------------------------------------------------------------


def test_create_run_adds_run_with_correct_fields() -> None:
    session = SessionStub()
    settings = Settings(sentiment_provider="mock", llm_api_key="", llm_model="gpt-4o-mini")
    service = QueryService(session=session, settings=settings)  # type: ignore[arg-type]

    run = asyncio.run(
        service.create_run(
            query_id="q-1",
            scope_config={"subreddits": ["linux"]},
            match_strategy="phrase_then_tokens",
            language_filter="EN",
        )
    )

    assert len(session.added) == 1
    assert run is session.added[0]
    assert run.query_id == "q-1"
    assert run.language_filter == "en"
    assert run.status == QueryRunStatus.pending
    assert run.sentiment_provider_name == "mock"


# ---------------------------------------------------------------------------
# requeue_stale_running_runs
# ---------------------------------------------------------------------------


def test_requeue_stale_running_runs_returns_zero_when_none_found() -> None:
    class _EmptySession:
        async def scalars(self, stmt: Any) -> list:
            return []

        async def flush(self) -> None:
            pass

    service = QueryService(session=_EmptySession())  # type: ignore[arg-type]

    result = asyncio.run(service.requeue_stale_running_runs(datetime.now(UTC)))

    assert result == 0
