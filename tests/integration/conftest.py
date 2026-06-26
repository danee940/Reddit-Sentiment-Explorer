from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Generator

import pytest
from fastapi import FastAPI

from reddit_sentiment.api import main as api_main
from reddit_sentiment.core.config import get_settings
from reddit_sentiment.db.init import initialize_database
from reddit_sentiment.db.models import QueryRun
from reddit_sentiment.db.session import get_engine, get_session_factory


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    url = os.environ.get("INTEGRATION_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set INTEGRATION_DATABASE_URL to a dedicated PostgreSQL URL "
            "(tests truncate application tables).",
        )
    return url


@pytest.fixture(scope="session")
def _integration_env(integration_database_url: str) -> Generator[None, None, None]:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = integration_database_url
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    yield
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture(scope="session")
def _migrated_db(_integration_env: None) -> None:
    asyncio.run(initialize_database())
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture
def clean_database(_migrated_db: None) -> Generator[None, None, None]:
    async def truncate() -> None:
        from sqlalchemy import text

        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE sentiment_results, query_document_matches, aggregates, "
                    "documents, comments, posts, query_runs, queries, subreddits "
                    "RESTART IDENTITY CASCADE"
                )
            )
        await engine.dispose()

    asyncio.run(truncate())
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    yield
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(truncate())
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture
def app(
    clean_database: None,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[FastAPI, None, None]:
    async def fake_initialize_database() -> None:
        return None

    monkeypatch.setattr(api_main, "initialize_database", fake_initialize_database)
    application = api_main.create_app()
    yield application
    application.dependency_overrides.clear()


def _run_db_op(coro_fn: Callable[[], object]) -> object:
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    result: object = asyncio.run(coro_fn())  # type: ignore[arg-type]
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    return result


@pytest.fixture
def complete_run(clean_database: None) -> Callable[[str], None]:
    from datetime import UTC, datetime, timedelta

    from reddit_sentiment.core.enums import QueryRunStatus

    async def _mark(run_id: str) -> None:
        factory = get_session_factory()
        async with factory() as session:
            run = await session.get(QueryRun, run_id)
            if run is None:
                return
            run.status = QueryRunStatus.completed
            now = datetime.now(UTC)
            run.finished_at = now
            run.data_fresh_until = now + timedelta(hours=1)
            await session.commit()
        await get_engine().dispose()

    def mark(run_id: str) -> None:
        _run_db_op(lambda: _mark(run_id))

    return mark


@pytest.fixture
def fail_run(clean_database: None) -> Callable[[str, str], None]:
    from datetime import UTC, datetime

    from reddit_sentiment.core.enums import QueryRunStatus

    async def _mark(run_id: str, error_message: str) -> None:
        factory = get_session_factory()
        async with factory() as session:
            run = await session.get(QueryRun, run_id)
            if run is None:
                return
            run.status = QueryRunStatus.failed
            run.finished_at = datetime.now(UTC)
            run.error_message = error_message
            await session.commit()
        await get_engine().dispose()

    def mark(run_id: str, error_message: str = "simulated failure") -> None:
        _run_db_op(lambda: _mark(run_id, error_message))

    return mark


@pytest.fixture
def stale_run(clean_database: None) -> Callable[[str], None]:
    from datetime import UTC, datetime, timedelta

    from reddit_sentiment.core.enums import QueryRunStatus

    async def _mark(run_id: str) -> None:
        factory = get_session_factory()
        async with factory() as session:
            run = await session.get(QueryRun, run_id)
            if run is None:
                return
            run.status = QueryRunStatus.completed
            now = datetime.now(UTC)
            run.finished_at = now - timedelta(hours=13)
            run.data_fresh_until = now - timedelta(hours=1)
            await session.commit()
        await get_engine().dispose()

    def mark(run_id: str) -> None:
        _run_db_op(lambda: _mark(run_id))

    return mark


@pytest.fixture
def fetch_run(clean_database: None) -> Callable[[str], QueryRun | None]:
    async def _get(run_id: str) -> QueryRun | None:
        factory = get_session_factory()
        async with factory() as session:
            run = await session.get(QueryRun, run_id)
        await get_engine().dispose()
        return run

    def get(run_id: str) -> QueryRun | None:
        return _run_db_op(lambda: _get(run_id))  # type: ignore[return-value]

    return get
