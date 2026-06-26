from __future__ import annotations

import asyncio
import fcntl
from typing import Any

import pytest

import reddit_sentiment.db.init as db_init_module


def test_should_stamp_when_alembic_version_absent_but_queries_present(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_has_table(table_name: str) -> bool:
        calls.append(table_name)
        if table_name == "alembic_version":
            return False
        if table_name == "queries":
            return True
        return False

    monkeypatch.setattr(db_init_module, "_has_table", fake_has_table)

    result = asyncio.run(db_init_module._should_stamp_existing_schema())

    assert result is True
    assert "alembic_version" in calls
    assert "queries" in calls


def test_no_stamp_when_alembic_version_present(monkeypatch) -> None:
    async def fake_has_table(table_name: str) -> bool:
        if table_name == "alembic_version":
            return True
        return False

    monkeypatch.setattr(db_init_module, "_has_table", fake_has_table)

    result = asyncio.run(db_init_module._should_stamp_existing_schema())

    assert result is False


def test_no_stamp_when_neither_alembic_nor_queries_table(monkeypatch) -> None:
    async def fake_has_table(table_name: str) -> bool:
        return False

    monkeypatch.setattr(db_init_module, "_has_table", fake_has_table)

    result = asyncio.run(db_init_module._should_stamp_existing_schema())

    assert result is False


def test_run_migration_command_stamps_and_upgrades_when_should_stamp(monkeypatch, tmp_path) -> None:
    stamp_calls: list[tuple] = []
    upgrade_calls: list[tuple] = []

    class FakeConfig:
        def __init__(self, path: str) -> None:
            self.path = path
            self._options: dict[str, str] = {}

        def set_main_option(self, key: str, value: str) -> None:
            self._options[key] = value

    def fake_stamp(config: Any, revision: str) -> None:
        stamp_calls.append((config, revision))

    def fake_upgrade(config: Any, revision: str) -> None:
        upgrade_calls.append((config, revision))

    def fake_flock(fd: int, operation: int) -> None:
        pass

    monkeypatch.setattr(db_init_module, "Config", FakeConfig)
    monkeypatch.setattr(db_init_module.command, "stamp", fake_stamp)
    monkeypatch.setattr(db_init_module.command, "upgrade", fake_upgrade)
    monkeypatch.setattr(fcntl, "flock", fake_flock)

    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\n")

    db_init_module._run_migration_command(tmp_path, should_stamp=True)

    assert len(stamp_calls) == 1
    assert stamp_calls[0][1] == db_init_module.ALEMBIC_BASELINE_REVISION
    assert len(upgrade_calls) == 1
    assert upgrade_calls[0][1] == "head"


def test_run_migration_command_skips_stamp_when_not_needed(monkeypatch, tmp_path) -> None:
    stamp_calls: list[tuple] = []
    upgrade_calls: list[tuple] = []

    class FakeConfig:
        def __init__(self, path: str) -> None:
            pass

        def set_main_option(self, key: str, value: str) -> None:
            pass

    monkeypatch.setattr(db_init_module, "Config", FakeConfig)
    monkeypatch.setattr(db_init_module.command, "stamp", lambda *a: stamp_calls.append(a))
    monkeypatch.setattr(db_init_module.command, "upgrade", lambda *a: upgrade_calls.append(a))
    monkeypatch.setattr(fcntl, "flock", lambda fd, op: None)

    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\n")

    db_init_module._run_migration_command(tmp_path, should_stamp=False)

    assert len(stamp_calls) == 0
    assert len(upgrade_calls) == 1


def test_run_migration_command_reraises_on_exception(monkeypatch, tmp_path) -> None:
    class FakeConfig:
        def __init__(self, path: str) -> None:
            pass

        def set_main_option(self, key: str, value: str) -> None:
            pass

    def bad_upgrade(config: Any, revision: str) -> None:
        raise RuntimeError("migration failed hard")

    monkeypatch.setattr(db_init_module, "Config", FakeConfig)
    monkeypatch.setattr(db_init_module.command, "stamp", lambda *a: None)
    monkeypatch.setattr(db_init_module.command, "upgrade", bad_upgrade)
    monkeypatch.setattr(fcntl, "flock", lambda fd, op: None)

    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\n")

    with pytest.raises(RuntimeError, match="migration failed hard"):
        db_init_module._run_migration_command(tmp_path, should_stamp=False)


def test_initialize_database_calls_migration_and_disposes_engine(monkeypatch) -> None:
    dispose_calls = [0]
    to_thread_calls: list[tuple] = []

    async def fake_should_stamp() -> bool:
        return False

    class FakeEngine:
        async def dispose(self) -> None:
            dispose_calls[0] += 1

    async def fake_to_thread(fn: Any, *args: Any) -> None:
        to_thread_calls.append((fn, args))

    monkeypatch.setattr(db_init_module, "_should_stamp_existing_schema", fake_should_stamp)
    monkeypatch.setattr(db_init_module, "engine", FakeEngine())
    monkeypatch.setattr(db_init_module, "to_thread", fake_to_thread)

    asyncio.run(db_init_module.initialize_database())

    assert dispose_calls[0] == 1
    assert len(to_thread_calls) == 1
    fn, args = to_thread_calls[0]
    assert fn is db_init_module._run_migration_command
    assert args[1] is False


def test_initialize_database_reraises_on_failure(monkeypatch) -> None:
    async def fake_should_stamp() -> bool:
        raise RuntimeError("db unreachable")

    monkeypatch.setattr(db_init_module, "_should_stamp_existing_schema", fake_should_stamp)

    with pytest.raises(RuntimeError, match="db unreachable"):
        asyncio.run(db_init_module.initialize_database())
