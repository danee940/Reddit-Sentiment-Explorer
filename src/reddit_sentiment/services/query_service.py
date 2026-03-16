from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.config import Settings, get_settings
from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.core.languages import DEFAULT_CONTENT_LANGUAGE, normalize_content_language
from reddit_sentiment.db.models import Query, QueryRun


def normalize_term(term: str) -> str:
    return " ".join(term.lower().strip().split())


class QueryService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()

    async def get_or_create_query(self, term: str) -> Query:
        normalized_term = normalize_term(term)
        stmt: Select[tuple[Query]] = select(Query).where(Query.normalized_term == normalized_term)
        query = await self.session.scalar(stmt)
        if query is not None:
            return query

        query = Query(raw_term=term, normalized_term=normalized_term)
        nested_transaction = await self.session.begin_nested()
        try:
            self.session.add(query)
            await self.session.flush()
        except IntegrityError:
            await nested_transaction.rollback()
            query = await self.session.scalar(stmt)
            if query is None:
                raise
        else:
            await nested_transaction.commit()
        return query

    async def create_run(
        self,
        query_id: str,
        scope_config: dict,
        match_strategy: str = "phrase_then_tokens",
        language_filter: str = DEFAULT_CONTENT_LANGUAGE,
    ) -> QueryRun:
        run = QueryRun(
            query_id=query_id,
            status=QueryRunStatus.pending,
            scope_config=scope_config,
            match_strategy=match_strategy,
            language_filter=normalize_content_language(language_filter),
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def mark_running(self, run: QueryRun) -> QueryRun:
        run.status = QueryRunStatus.running
        run.started_at = datetime.now(UTC)
        run.error_message = None
        run.finished_at = None
        await self.session.flush()
        return run

    async def mark_completed(self, run: QueryRun) -> QueryRun:
        run.status = QueryRunStatus.completed
        now = datetime.now(UTC)
        run.finished_at = now
        run.data_fresh_until = now + timedelta(hours=self.settings.query_cache_ttl_hours)
        await self.session.flush()
        return run

    async def mark_failed(self, run: QueryRun, error_message: str) -> QueryRun:
        run.status = QueryRunStatus.failed
        run.finished_at = datetime.now(UTC)
        run.error_message = error_message
        await self.session.flush()
        return run

    async def get_run(self, run_id: str) -> QueryRun | None:
        return await self.session.get(QueryRun, run_id)

    async def requeue_stale_running_runs(self, stale_before: datetime) -> int:
        stmt: Select[tuple[QueryRun]] = (
            select(QueryRun)
            .where(QueryRun.status == QueryRunStatus.running)
            .where(QueryRun.started_at < stale_before)
        )
        runs = list(await self.session.scalars(stmt))
        for run in runs:
            run.status = QueryRunStatus.pending
            run.finished_at = None
            run.error_message = None
        if runs:
            await self.session.flush()
        return len(runs)

    async def claim_next_pending_run(self) -> QueryRun | None:
        stmt: Select[tuple[QueryRun]] = (
            select(QueryRun)
            .where(QueryRun.status == QueryRunStatus.pending)
            .order_by(QueryRun.started_at)
            .with_for_update(skip_locked=True)
        )
        run = await self.session.scalar(stmt)
        if run is None:
            return None
        await self.mark_running(run)
        return run
