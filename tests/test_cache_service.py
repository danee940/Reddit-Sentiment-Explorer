from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.services.cache_service import CacheService


@dataclass
class QueryRunStub:
    id: str
    query_id: str
    status: QueryRunStatus
    language_filter: str
    sentiment_provider_name: str
    sentiment_provider_version: str
    data_fresh_until: datetime | None
    scope_config: dict = field(default_factory=dict)
    started_at: datetime | None = None


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def _past() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


class _ScalarsResult:
    def __init__(self, runs: list[QueryRunStub]) -> None:
        self._runs = runs

    def all(self) -> list[QueryRunStub]:
        return self._runs


class SessionStub:
    def __init__(self, runs: list[QueryRunStub]) -> None:
        self._runs = runs

    async def scalars(self, stmt: Any) -> _ScalarsResult:
        return _ScalarsResult(self._runs)


def _service(runs: list[QueryRunStub]) -> CacheService:
    return CacheService(session=SessionStub(runs))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_fresh_run — matching run returned
# ---------------------------------------------------------------------------


def test_get_fresh_run_returns_matching_run() -> None:
    scope = {"subreddits": ["linux"]}
    run = QueryRunStub(
        id="run-1",
        query_id="q-1",
        status=QueryRunStatus.completed,
        language_filter="en",
        sentiment_provider_name="mock",
        sentiment_provider_version="heuristic-v3",
        data_fresh_until=_future(),
        scope_config=scope,
    )
    service = _service([run])

    result = asyncio.run(
        service.get_fresh_run(
            query_id="q-1",
            scope_config=scope,
            language_filter="en",
            sentiment_provider_name="mock",
            sentiment_provider_version="heuristic-v3",
        )
    )

    assert result is run


# ---------------------------------------------------------------------------
# get_fresh_run — scope mismatch returns None
# ---------------------------------------------------------------------------


def test_get_fresh_run_returns_none_when_scope_differs() -> None:
    run = QueryRunStub(
        id="run-1",
        query_id="q-1",
        status=QueryRunStatus.completed,
        language_filter="en",
        sentiment_provider_name="mock",
        sentiment_provider_version="heuristic-v3",
        data_fresh_until=_future(),
        scope_config={"subreddits": ["linux"]},
    )
    service = _service([run])

    result = asyncio.run(
        service.get_fresh_run(
            query_id="q-1",
            scope_config={"subreddits": ["python"]},
            language_filter="en",
            sentiment_provider_name="mock",
            sentiment_provider_version="heuristic-v3",
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# get_fresh_run — no runs at all
# ---------------------------------------------------------------------------


def test_get_fresh_run_returns_none_when_no_runs() -> None:
    service = _service([])

    result = asyncio.run(
        service.get_fresh_run(
            query_id="q-1",
            scope_config={"subreddits": ["linux"]},
            language_filter="en",
            sentiment_provider_name="mock",
            sentiment_provider_version="heuristic-v3",
        )
    )

    assert result is None


# ---------------------------------------------------------------------------
# get_fresh_run — picks first matching scope from multiple candidates
# ---------------------------------------------------------------------------


def test_get_fresh_run_picks_first_scope_match_among_multiple() -> None:
    scope = {"subreddits": ["linux"]}
    run_a = QueryRunStub(
        id="run-a",
        query_id="q-1",
        status=QueryRunStatus.completed,
        language_filter="en",
        sentiment_provider_name="mock",
        sentiment_provider_version="heuristic-v3",
        data_fresh_until=_future(),
        scope_config={"subreddits": ["python"]},
    )
    run_b = QueryRunStub(
        id="run-b",
        query_id="q-1",
        status=QueryRunStatus.completed,
        language_filter="en",
        sentiment_provider_name="mock",
        sentiment_provider_version="heuristic-v3",
        data_fresh_until=_future(),
        scope_config=scope,
    )
    service = _service([run_a, run_b])

    result = asyncio.run(
        service.get_fresh_run(
            query_id="q-1",
            scope_config=scope,
            language_filter="en",
            sentiment_provider_name="mock",
            sentiment_provider_version="heuristic-v3",
        )
    )

    assert result is run_b
