from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.core.languages import normalize_content_language
from reddit_sentiment.db.models import QueryRun


class CacheService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_fresh_run(
        self,
        query_id: str,
        scope_config: dict,
        language_filter: str,
        sentiment_provider_name: str,
        sentiment_provider_version: str,
    ) -> QueryRun | None:
        now = datetime.now(UTC)
        normalized_language = normalize_content_language(language_filter)
        stmt = (
            select(QueryRun)
            .where(QueryRun.query_id == query_id)
            .where(QueryRun.status == QueryRunStatus.completed)
            .where(QueryRun.language_filter == normalized_language)
            .where(QueryRun.sentiment_provider_name == sentiment_provider_name)
            .where(QueryRun.sentiment_provider_version == sentiment_provider_version)
            .where(QueryRun.data_fresh_until >= now)
            .order_by(desc(QueryRun.started_at))
        )
        runs = (await self.session.scalars(stmt)).all()
        for run in runs:
            if run.scope_config == scope_config:
                return run
        return None