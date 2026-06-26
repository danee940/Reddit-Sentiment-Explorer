from __future__ import annotations

import fcntl
import logging
from asyncio import to_thread
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from reddit_sentiment.db.session import engine

logger = logging.getLogger(__name__)

MIGRATION_LOCK_PATH = Path("/tmp/reddit_sentiment_migrations.lock")
ALEMBIC_BASELINE_REVISION = "0001_initial"


async def _has_table(table_name: str) -> bool:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = :table_name
                )
                """
            ),
            {"table_name": table_name},
        )
        return bool(result.scalar())


async def _should_stamp_existing_schema() -> bool:
    logger.info("Checking existing schema state")
    has_alembic_version = await _has_table("alembic_version")
    if has_alembic_version:
        logger.info("alembic_version table found, skipping stamp")
        return False
    has_queries = await _has_table("queries")
    logger.info("queries table present=%s, stamp needed=%s", has_queries, has_queries)
    return has_queries


def _run_migration_command(root_path: Path, should_stamp: bool) -> None:
    try:
        alembic_config = Config(str(root_path / "alembic.ini"))
        alembic_config.set_main_option(
            "script_location",
            str(root_path / "src/reddit_sentiment/db/migrations"),
        )
        MIGRATION_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MIGRATION_LOCK_PATH.open("w", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            if should_stamp:
                logger.info("Stamping schema to baseline revision %s", ALEMBIC_BASELINE_REVISION)
                command.stamp(alembic_config, ALEMBIC_BASELINE_REVISION)
            logger.info("Running Alembic upgrade to head")
            command.upgrade(alembic_config, "head")
            logger.info("Migrations complete")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    except Exception:
        logger.exception("Migration command failed")
        raise


async def initialize_database() -> None:
    logger.info("Initializing database")
    try:
        root_path = Path(__file__).resolve().parents[3]
        should_stamp = await _should_stamp_existing_schema()
        await to_thread(_run_migration_command, root_path, should_stamp)
        await engine.dispose()
        logger.info("Database initialization complete")
    except Exception:
        logger.exception("Database initialization failed")
        raise
