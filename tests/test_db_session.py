from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment",
)

import reddit_sentiment.db.session as session_module


def test_get_engine_returns_async_engine(monkeypatch) -> None:
    session_module.get_engine.cache_clear()

    fake_engine = MagicMock(name="fake_engine")
    fake_create = MagicMock(return_value=fake_engine)

    monkeypatch.setattr(session_module, "create_async_engine", fake_create)

    result = session_module.get_engine()

    assert result is fake_engine
    fake_create.assert_called_once()
    call_kwargs = fake_create.call_args
    assert call_kwargs is not None

    session_module.get_engine.cache_clear()


def test_get_session_factory_returns_sessionmaker(monkeypatch) -> None:
    session_module.get_engine.cache_clear()
    session_module.get_session_factory.cache_clear()

    fake_engine = MagicMock(name="fake_engine")
    fake_factory = MagicMock(name="fake_factory")
    fake_sessionmaker = MagicMock(return_value=fake_factory)

    monkeypatch.setattr(session_module, "create_async_engine", MagicMock(return_value=fake_engine))
    monkeypatch.setattr(session_module, "async_sessionmaker", fake_sessionmaker)

    result = session_module.get_session_factory()

    assert result is fake_factory

    session_module.get_engine.cache_clear()
    session_module.get_session_factory.cache_clear()


def test_create_session_calls_factory(monkeypatch) -> None:
    fake_session = MagicMock(name="fake_session")
    fake_factory = MagicMock(return_value=fake_session)

    monkeypatch.setattr(session_module, "get_session_factory", lambda: fake_factory)

    result = session_module.create_session()

    assert result is fake_session
    fake_factory.assert_called_once()


def test_lazy_engine_proxy_delegates_attribute() -> None:
    fake_engine = MagicMock(name="fake_engine")
    fake_engine.dialect = "postgresql"

    with patch.object(session_module, "get_engine", return_value=fake_engine):
        proxy = session_module._LazyEngineProxy()
        result = proxy.dialect

    assert result == "postgresql"


def test_get_db_session_commits_on_success() -> None:
    commit_calls = [0]
    rollback_calls = [0]

    class FakeSession:
        async def commit(self) -> None:
            commit_calls[0] += 1

        async def rollback(self) -> None:
            rollback_calls[0] += 1

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            pass

    fake_session = FakeSession()

    async def _run_generator() -> None:
        async for session in session_module.get_db_session():
            assert session is fake_session

    with patch.object(session_module, "create_session", return_value=fake_session):
        asyncio.run(_run_generator())

    assert commit_calls[0] == 1
    assert rollback_calls[0] == 0


def test_get_db_session_rolls_back_on_exception() -> None:
    commit_calls = [0]
    rollback_calls = [0]

    class FakeSession:
        async def commit(self) -> None:
            commit_calls[0] += 1

        async def rollback(self) -> None:
            rollback_calls[0] += 1

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            pass

    fake_session = FakeSession()

    async def _run_generator_with_error() -> None:
        gen = cast(AsyncGenerator, session_module.get_db_session())
        await gen.__anext__()
        try:
            raise ValueError("something went wrong")
        except ValueError:
            try:
                await gen.athrow(ValueError("something went wrong"))
            except (ValueError, StopAsyncIteration):
                pass
        raise ValueError("something went wrong")

    with patch.object(session_module, "create_session", return_value=fake_session):
        with pytest.raises(ValueError, match="something went wrong"):
            asyncio.run(_run_generator_with_error())

    assert commit_calls[0] == 0
    assert rollback_calls[0] == 1
