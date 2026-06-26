from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment",
)

from fastapi import HTTPException

from reddit_sentiment.api import dependencies as deps


class SessionStub:
    pass


class SettingsStub:
    pass


class QueryRunStub:
    def __init__(self, query_id: str = "q-1") -> None:
        self.id = "run-1"
        self.query_id = query_id


class QueryStub:
    def __init__(self) -> None:
        self.id = "q-1"


class QueryServiceStub:
    pass


class QueryReadServiceStub:
    pass


class CacheServiceStub:
    pass


class AggregationServiceStub:
    pass


class SubredditServiceStub:
    pass


def test_get_query_service_returns_service(monkeypatch) -> None:
    session = SessionStub()
    settings = SettingsStub()
    expected = QueryServiceStub()

    monkeypatch.setattr(deps, "create_query_service", lambda s, ss: expected)

    result = deps.get_query_service(session, settings)  # type: ignore[arg-type]
    assert result is expected


def test_get_query_read_service_returns_service(monkeypatch) -> None:
    session = SessionStub()
    expected = QueryReadServiceStub()

    monkeypatch.setattr(deps, "create_query_read_service", lambda s: expected)

    result = deps.get_query_read_service(session)  # type: ignore[arg-type]
    assert result is expected


def test_get_cache_service_returns_service(monkeypatch) -> None:
    session = SessionStub()
    expected = CacheServiceStub()

    monkeypatch.setattr(deps, "create_cache_service", lambda s: expected)

    result = deps.get_cache_service(session)  # type: ignore[arg-type]
    assert result is expected


def test_get_aggregation_service_returns_service(monkeypatch) -> None:
    session = SessionStub()
    expected = AggregationServiceStub()

    monkeypatch.setattr(deps, "create_aggregation_service", lambda s: expected)

    result = deps.get_aggregation_service(session)  # type: ignore[arg-type]
    assert result is expected


def test_get_subreddit_service_returns_service(monkeypatch) -> None:
    expected = SubredditServiceStub()

    monkeypatch.setattr(deps, "create_subreddit_service", lambda: expected)

    result = deps.get_subreddit_service()
    assert result is expected


class _FoundReadService:
    def __init__(self, run: Any) -> None:
        self._run = run

    async def get_latest_run_for_provider(self, query_id: str, name: str, version: str) -> Any:
        return self._run

    async def get_run(self, run_id: str) -> Any:
        return self._run

    async def get_query(self, query_id: str) -> Any:
        return QueryStub()


class _MissingReadService:
    async def get_latest_run_for_provider(self, query_id: str, name: str, version: str) -> None:
        return None

    async def get_run(self, run_id: str) -> None:
        return None

    async def get_query(self, query_id: str) -> None:
        return None


class _SettingsWithMock:
    sentiment_provider = "mock"
    llm_api_key = ""
    llm_model = "gpt-4o-mini"


def test_get_latest_query_run_or_404_returns_run_when_found(monkeypatch) -> None:
    run = QueryRunStub()

    monkeypatch.setattr(
        deps, "sentiment_provider_identity", lambda s: ("mock", "heuristic-v3")
    )

    result = asyncio.run(
        deps.get_latest_query_run_or_404(
            query_id="q-1",
            query_read_service=_FoundReadService(run),  # type: ignore[arg-type]
            settings=_SettingsWithMock(),  # type: ignore[arg-type]
        )
    )
    assert result is run


def test_get_latest_query_run_or_404_raises_404_when_not_found(monkeypatch) -> None:
    monkeypatch.setattr(
        deps, "sentiment_provider_identity", lambda s: ("mock", "heuristic-v3")
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            deps.get_latest_query_run_or_404(
                query_id="missing",
                query_read_service=_MissingReadService(),  # type: ignore[arg-type]
                settings=_SettingsWithMock(),  # type: ignore[arg-type]
            )
        )
    assert exc_info.value.status_code == 404


def test_get_query_run_or_404_returns_run_when_found() -> None:
    run = QueryRunStub()
    result = asyncio.run(
        deps.get_query_run_or_404(
            run_id="run-1",
            query_read_service=_FoundReadService(run),  # type: ignore[arg-type]
        )
    )
    assert result is run


def test_get_query_run_or_404_raises_404_when_not_found() -> None:
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            deps.get_query_run_or_404(
                run_id="missing",
                query_read_service=_MissingReadService(),  # type: ignore[arg-type]
            )
        )
    assert exc_info.value.status_code == 404


def test_get_query_for_run_or_404_returns_query_when_found() -> None:
    run = QueryRunStub(query_id="q-1")
    result = asyncio.run(
        deps.get_query_for_run_or_404(
            run=run,  # type: ignore[arg-type]
            query_read_service=_FoundReadService(run),  # type: ignore[arg-type]
        )
    )
    assert isinstance(result, QueryStub)


def test_get_query_for_run_or_404_raises_404_when_query_not_found() -> None:
    run = QueryRunStub(query_id="q-1")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            deps.get_query_for_run_or_404(
                run=run,  # type: ignore[arg-type]
                query_read_service=_MissingReadService(),  # type: ignore[arg-type]
            )
        )
    assert exc_info.value.status_code == 404
