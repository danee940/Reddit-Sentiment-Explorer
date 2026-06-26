from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.services.query_service import QueryService


@dataclass
class QueryRunStub:
    id: str = "run-1"
    query_id: str = "q-1"
    status: QueryRunStatus = QueryRunStatus.running
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    error_message: str | None = None
    data_fresh_until: datetime | None = None
    scope_config: dict = field(default_factory=dict)
    match_strategy: str = "phrase_then_tokens"
    language_filter: str = "en"
    sentiment_provider_name: str = "mock"
    sentiment_provider_version: str = "heuristic-v3"


class _NestedTransaction:
    def __init__(self) -> None:
        self.rolled_back = False
        self.committed = False

    async def rollback(self) -> None:
        self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True


class _IntegrityErrorSession:
    def __init__(self, refetch_result: Any = None) -> None:
        self._refetch_result = refetch_result
        self.added: list[Any] = []
        self.flush_calls = 0
        self._nested = _NestedTransaction()
        self._first_scalar = True

    async def scalar(self, stmt: Any) -> Any:
        if self._first_scalar:
            self._first_scalar = False
            return None
        return self._refetch_result

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def all(self) -> list:
                return []

        return _Result()

    async def get(self, model: Any, pk: Any) -> Any:
        return None

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flush_calls += 1
        raise IntegrityError(None, None, Exception("duplicate key"))

    async def begin_nested(self) -> _NestedTransaction:
        return self._nested


def test_get_or_create_query_handles_integrity_error_and_refetches() -> None:
    from dataclasses import dataclass

    @dataclass
    class ExistingQuery:
        id: str = "q-existing"
        raw_term: str = "linux"
        normalized_term: str = "linux"

    existing = ExistingQuery()
    session = _IntegrityErrorSession(refetch_result=existing)
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.get_or_create_query("Linux"))

    assert result is existing
    assert session._nested.rolled_back is True


def test_get_or_create_query_reraises_when_refetch_returns_none() -> None:
    session = _IntegrityErrorSession(refetch_result=None)
    service = QueryService(session=session)  # type: ignore[arg-type]

    try:
        asyncio.run(service.get_or_create_query("Linux"))
        raise AssertionError("expected IntegrityError to be raised")
    except IntegrityError:
        pass

    assert session._nested.rolled_back is True


class _RunsFoundSession:
    def __init__(self, runs: list[Any]) -> None:
        self._runs = runs
        self.flush_calls = 0

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, items: list) -> None:
                self._items = items

            def __iter__(self):  # type: ignore[no-untyped-def]
                return iter(self._items)

        return _Result(self._runs)

    async def flush(self) -> None:
        self.flush_calls += 1

    async def scalar(self, stmt: Any) -> Any:
        return None

    async def get(self, model: Any, pk: Any) -> Any:
        return None

    def add(self, obj: Any) -> None:
        pass

    async def begin_nested(self) -> _NestedTransaction:
        return _NestedTransaction()


def test_requeue_stale_running_runs_resets_status_and_flushes() -> None:
    runs = [QueryRunStub(id="run-1"), QueryRunStub(id="run-2")]
    session = _RunsFoundSession(runs)
    service = QueryService(session=session)  # type: ignore[arg-type]

    count = asyncio.run(service.requeue_stale_running_runs(datetime.now(UTC)))

    assert count == 2
    for run in runs:
        assert run.status == QueryRunStatus.pending
        assert run.finished_at is None
        assert run.error_message is None
    assert session.flush_calls == 1


class _PendingRunSession:
    def __init__(self, run: Any) -> None:
        self._run = run
        self.flush_calls = 0

    async def scalar(self, stmt: Any) -> Any:
        return self._run

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def all(self) -> list:
                return []

        return _Result()

    async def get(self, model: Any, pk: Any) -> Any:
        return None

    def add(self, obj: Any) -> None:
        pass

    async def flush(self) -> None:
        self.flush_calls += 1

    async def begin_nested(self) -> _NestedTransaction:
        return _NestedTransaction()


def test_claim_next_pending_run_returns_run_and_marks_running() -> None:
    run = QueryRunStub(status=QueryRunStatus.pending, started_at=None)  # type: ignore[arg-type]
    session = _PendingRunSession(run)
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.claim_next_pending_run())

    assert result is run
    assert run.status == QueryRunStatus.running
    assert session.flush_calls >= 1


class _NoPendingRunSession:
    async def scalar(self, stmt: Any) -> None:
        return None

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def all(self) -> list:
                return []

        return _Result()

    async def get(self, model: Any, pk: Any) -> None:
        return None

    def add(self, obj: Any) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def begin_nested(self) -> _NestedTransaction:
        return _NestedTransaction()


def test_claim_next_pending_run_returns_none_when_no_run() -> None:
    session = _NoPendingRunSession()
    service = QueryService(session=session)  # type: ignore[arg-type]

    result = asyncio.run(service.claim_next_pending_run())

    assert result is None
