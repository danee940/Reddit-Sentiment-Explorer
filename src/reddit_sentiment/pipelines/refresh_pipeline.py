from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.db.models import QueryRun
from reddit_sentiment.pipelines.run_query_pipeline import run_query_pipeline


async def refresh_query_run(
    session: AsyncSession,
    query_run: QueryRun,
    term: str,
    subreddit_names: list[str],
) -> None:
    await run_query_pipeline(
        session=session,
        query_run=query_run,
        term=term,
        subreddit_names=subreddit_names,
    )
