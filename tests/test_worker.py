import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import cast

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment"
)

from reddit_sentiment import worker


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

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class RunStub:
    def __init__(self) -> None:
        self.id = "run-1"
        self.query_id = "query-1"
        self.scope_config = {"subreddits": ["hungary"]}
        self.status = None
        self.error_message = None


def test_recover_stale_runs_requeues_old_running_runs(monkeypatch) -> None:
    session = SessionStub()
    tracker: dict[str, object] = {}

    class QueryServiceStub:
        def __init__(self, session_arg) -> None:
            tracker["session_arg"] = session_arg

        async def requeue_stale_running_runs(self, stale_before: datetime) -> int:
            tracker["stale_before"] = stale_before
            return 2

    monkeypatch.setattr(
        worker,
        "get_session_factory",
        lambda: lambda: SessionContextStub(session),
    )
    monkeypatch.setattr(
        worker,
        "create_query_service",
        lambda session_arg: QueryServiceStub(session_arg),
    )

    before_call = datetime.now(UTC) - timedelta(minutes=30, seconds=1)
    recovered = asyncio.run(worker.recover_stale_runs(30))
    after_call = datetime.now(UTC) - timedelta(minutes=30) + timedelta(seconds=1)

    assert recovered == 2
    assert tracker["session_arg"] is session
    stale_before = cast(datetime, tracker["stale_before"])
    assert before_call <= stale_before <= after_call
    assert session.commit_calls == 1


def test_process_run_marks_missing_query_failed(monkeypatch) -> None:
    session = SessionStub()
    run = RunStub()

    class QueryReadServiceStub:
        async def get_run(self, run_id: str):
            assert run_id == "run-1"
            return run

        async def get_query(self, query_id: str):
            assert query_id == "query-1"
            return None

    async def unexpected_run_query_pipeline(**kwargs) -> None:
        raise AssertionError("pipeline should not run when the query is missing")

    monkeypatch.setattr(
        worker,
        "get_session_factory",
        lambda: lambda: SessionContextStub(session),
    )
    monkeypatch.setattr(
        worker,
        "create_query_read_service",
        lambda session_arg: QueryReadServiceStub(),
    )
    monkeypatch.setattr(worker, "run_query_pipeline", unexpected_run_query_pipeline)

    asyncio.run(worker.process_run("run-1"))

    assert run.status == worker.QueryRunStatus.failed
    assert run.error_message == "Query not found."
    assert session.commit_calls == 1
