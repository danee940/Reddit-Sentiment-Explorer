from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from reddit_sentiment.composition import (
    create_query_pipeline_services,
    create_query_read_service,
    create_query_service,
)
from reddit_sentiment.core.config import get_settings
from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.core.logging import configure_logging
from reddit_sentiment.db.init import initialize_database
from reddit_sentiment.db.session import get_session_factory
from reddit_sentiment.pipelines.run_query_pipeline import run_query_pipeline

logger = logging.getLogger(__name__)


async def recover_stale_runs(stale_after_minutes: int) -> int:
    stale_before = datetime.now(UTC) - timedelta(minutes=stale_after_minutes)
    async with get_session_factory()() as session:
        query_service = create_query_service(session)
        recovered_runs = await query_service.requeue_stale_running_runs(stale_before)
        if recovered_runs:
            await session.commit()
            logger.warning(
                "requeued_stale_query_runs count=%s stale_after_minutes=%s",
                recovered_runs,
                stale_after_minutes,
            )
        return recovered_runs


async def claim_next_pending_run_id() -> str | None:
    async with get_session_factory()() as session:
        query_service = create_query_service(session)
        run = await query_service.claim_next_pending_run()
        if run is None:
            return None
        await session.commit()
        return run.id


async def process_run(run_id: str) -> None:
    async with get_session_factory()() as session:
        query_read_service = create_query_read_service(session)
        run = await query_read_service.get_run(run_id)
        if run is None:
            return

        query = await query_read_service.get_query(run.query_id)
        if query is None:
            run.status = QueryRunStatus.failed
            run.error_message = "Query not found."
            await session.commit()
            return

        logger.info("Processing run %s", run.id)
        await run_query_pipeline(
            session=session,
            query_run=run,
            term=query.raw_term,
            subreddit_names=run.scope_config.get("subreddits", []),
            services=create_query_pipeline_services(session, query.raw_term),
        )


async def process_pending_runs(poll_interval: int = 10) -> None:
    await initialize_database()
    settings = get_settings()
    await recover_stale_runs(settings.query_run_stale_after_minutes)
    while True:
        processed_any = False
        while True:
            run_id = await claim_next_pending_run_id()
            if run_id is None:
                break
            processed_any = True
            await process_run(run_id)
        if not processed_any:
            await asyncio.sleep(poll_interval)


def main() -> None:
    configure_logging()
    asyncio.run(process_pending_runs())


if __name__ == "__main__":
    main()
