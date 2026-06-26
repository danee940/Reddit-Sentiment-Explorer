from __future__ import annotations

import asyncio
import os
from typing import Any

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment",
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

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


def test_process_pending_runs_stops_after_one_sleep(monkeypatch) -> None:
    call_log: list[str] = []
    sleep_count = [0]

    async def fake_initialize_database() -> None:
        call_log.append("initialize_database")

    class FakeSettings:
        query_run_stale_after_minutes = 30

    async def fake_recover_stale_runs(minutes: int) -> int:
        call_log.append("recover_stale_runs")
        return 0

    async def fake_claim_next_pending_run_id() -> str | None:
        call_log.append("claim_next_pending_run_id")
        return None

    async def fake_sleep(seconds: float) -> None:
        sleep_count[0] += 1
        if sleep_count[0] >= 1:
            raise StopAsyncIteration("stop")

    monkeypatch.setattr(worker, "initialize_database", fake_initialize_database)
    monkeypatch.setattr(worker, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(worker, "recover_stale_runs", fake_recover_stale_runs)
    monkeypatch.setattr(worker, "claim_next_pending_run_id", fake_claim_next_pending_run_id)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(worker.process_pending_runs(poll_interval=1))
    except StopAsyncIteration:
        pass

    assert "initialize_database" in call_log
    assert "recover_stale_runs" in call_log
    assert "claim_next_pending_run_id" in call_log
    assert sleep_count[0] == 1


def test_process_pending_runs_processes_run_before_sleeping(monkeypatch) -> None:
    processed_ids: list[str] = []
    run_ids_queue = ["run-1", None]
    queue_index = [0]
    sleep_count = [0]

    async def fake_initialize_database() -> None:
        pass

    class FakeSettings:
        query_run_stale_after_minutes = 30

    async def fake_recover_stale_runs(minutes: int) -> int:
        return 0

    async def fake_claim_next_pending_run_id() -> str | None:
        idx = queue_index[0]
        queue_index[0] += 1
        if idx < len(run_ids_queue):
            return run_ids_queue[idx]
        return None

    async def fake_process_run(run_id: str) -> None:
        processed_ids.append(run_id)

    async def fake_sleep(seconds: float) -> None:
        sleep_count[0] += 1
        raise StopAsyncIteration("stop")

    monkeypatch.setattr(worker, "initialize_database", fake_initialize_database)
    monkeypatch.setattr(worker, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(worker, "recover_stale_runs", fake_recover_stale_runs)
    monkeypatch.setattr(worker, "claim_next_pending_run_id", fake_claim_next_pending_run_id)
    monkeypatch.setattr(worker, "process_run", fake_process_run)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    try:
        asyncio.run(worker.process_pending_runs(poll_interval=1))
    except StopAsyncIteration:
        pass

    assert processed_ids == ["run-1"]
    assert sleep_count[0] == 1


def test_main_calls_configure_logging_and_runs_loop(monkeypatch) -> None:
    configure_logging_calls = [0]
    asyncio_run_calls: list[Any] = []

    def fake_configure_logging() -> None:
        configure_logging_calls[0] += 1

    async def fake_process_pending_runs(poll_interval: int = 10) -> None:
        pass

    monkeypatch.setattr(worker, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(worker, "process_pending_runs", fake_process_pending_runs)
    monkeypatch.setattr(asyncio, "run", lambda coro: asyncio_run_calls.append(coro))

    worker.main()

    assert configure_logging_calls[0] == 1
    assert len(asyncio_run_calls) == 1
