from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment",
)

from reddit_sentiment import worker
from reddit_sentiment.core.enums import QueryRunStatus

# ---------------------------------------------------------------------------
# Shared stubs
# ---------------------------------------------------------------------------


class SessionStub:
    def __init__(self) -> None:
        self.commit_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1


class SessionContextStub:
    def __init__(self, session: SessionStub) -> None:
        self.session = session

    async def __aenter__(self) -> SessionStub:
        return self.session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


@dataclass
class RunStub:
    id: str = "run-1"
    query_id: str = "query-1"
    scope_config: dict = None  # type: ignore[assignment]
    status: Any = QueryRunStatus.pending
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.scope_config is None:
            self.scope_config = {"subreddits": ["linux"]}


@dataclass
class QueryStub:
    id: str = "query-1"
    raw_term: str = "linux"


# ---------------------------------------------------------------------------
# claim_next_pending_run_id — no pending run
# ---------------------------------------------------------------------------


def test_claim_next_pending_run_id_returns_none_when_no_run(monkeypatch) -> None:
    session = SessionStub()

    class QueryServiceStub:
        async def claim_next_pending_run(self) -> None:
            return None

    monkeypatch.setattr(worker, "get_session_factory", lambda: lambda: SessionContextStub(session))
    monkeypatch.setattr(worker, "create_query_service", lambda s: QueryServiceStub())

    result = asyncio.run(worker.claim_next_pending_run_id())

    assert result is None
    assert session.commit_calls == 0


# ---------------------------------------------------------------------------
# claim_next_pending_run_id — run found
# ---------------------------------------------------------------------------


def test_claim_next_pending_run_id_returns_run_id_and_commits(monkeypatch) -> None:
    session = SessionStub()
    run = RunStub(id="run-42")

    class QueryServiceStub:
        async def claim_next_pending_run(self) -> RunStub:
            return run

    monkeypatch.setattr(worker, "get_session_factory", lambda: lambda: SessionContextStub(session))
    monkeypatch.setattr(worker, "create_query_service", lambda s: QueryServiceStub())

    result = asyncio.run(worker.claim_next_pending_run_id())

    assert result == "run-42"
    assert session.commit_calls == 1


# ---------------------------------------------------------------------------
# process_run — run not found
# ---------------------------------------------------------------------------


def test_process_run_does_nothing_when_run_not_found(monkeypatch) -> None:
    session = SessionStub()

    class QueryReadServiceStub:
        async def get_run(self, run_id: str) -> None:
            return None

        async def get_query(self, query_id: str) -> None:
            return None

    async def unexpected_pipeline(**kwargs: Any) -> None:
        raise AssertionError("pipeline should not run when run is missing")

    monkeypatch.setattr(worker, "get_session_factory", lambda: lambda: SessionContextStub(session))
    monkeypatch.setattr(worker, "create_query_read_service", lambda s: QueryReadServiceStub())
    monkeypatch.setattr(worker, "run_query_pipeline", unexpected_pipeline)

    asyncio.run(worker.process_run("missing-run"))

    assert session.commit_calls == 0


# ---------------------------------------------------------------------------
# process_run — success path
# ---------------------------------------------------------------------------


def test_process_run_runs_pipeline_on_success(monkeypatch) -> None:
    session = SessionStub()
    run = RunStub()
    query = QueryStub()
    pipeline_called_with: dict = {}

    class QueryReadServiceStub:
        async def get_run(self, run_id: str) -> RunStub:
            assert run_id == "run-1"
            return run

        async def get_query(self, query_id: str) -> QueryStub:
            assert query_id == "query-1"
            return query

    async def fake_pipeline(**kwargs: Any) -> None:
        pipeline_called_with.update(kwargs)

    monkeypatch.setattr(worker, "get_session_factory", lambda: lambda: SessionContextStub(session))
    monkeypatch.setattr(worker, "create_query_read_service", lambda s: QueryReadServiceStub())
    monkeypatch.setattr(worker, "create_query_pipeline_services", lambda *a, **kw: object())
    monkeypatch.setattr(worker, "run_query_pipeline", fake_pipeline)

    asyncio.run(worker.process_run("run-1"))

    assert "query_run" in pipeline_called_with
    assert pipeline_called_with["term"] == "linux"


# ---------------------------------------------------------------------------
# recover_stale_runs — no stale runs
# ---------------------------------------------------------------------------


def test_recover_stale_runs_does_not_commit_when_count_is_zero(monkeypatch) -> None:
    session = SessionStub()

    class QueryServiceStub:
        async def requeue_stale_running_runs(self, stale_before: Any) -> int:
            return 0

    monkeypatch.setattr(worker, "get_session_factory", lambda: lambda: SessionContextStub(session))
    monkeypatch.setattr(worker, "create_query_service", lambda s: QueryServiceStub())

    result = asyncio.run(worker.recover_stale_runs(30))

    assert result == 0
    assert session.commit_calls == 0
