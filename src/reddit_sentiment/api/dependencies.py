from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.composition import (
    create_aggregation_service,
    create_cache_service,
    create_query_read_service,
    create_query_service,
    create_subreddit_service,
    get_app_settings,
)
from reddit_sentiment.core.config import Settings
from reddit_sentiment.db.models import Query, QueryRun
from reddit_sentiment.db.session import get_db_session
from reddit_sentiment.sentiment.provider_identity import sentiment_provider_identity
from reddit_sentiment.services.aggregation_service import AggregationService
from reddit_sentiment.services.cache_service import CacheService
from reddit_sentiment.services.query_read_service import QueryReadService
from reddit_sentiment.services.query_service import QueryService
from reddit_sentiment.services.subreddit_service import SubredditService

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_query_service(session: DBSession, settings: SettingsDep) -> QueryService:
    return create_query_service(session, settings)


def get_query_read_service(session: DBSession) -> QueryReadService:
    return create_query_read_service(session)


def get_cache_service(session: DBSession) -> CacheService:
    return create_cache_service(session)


def get_aggregation_service(session: DBSession) -> AggregationService:
    return create_aggregation_service(session)


def get_subreddit_service() -> SubredditService:
    return create_subreddit_service()


QueryServiceDep = Annotated[QueryService, Depends(get_query_service)]
QueryReadServiceDep = Annotated[QueryReadService, Depends(get_query_read_service)]
CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]
AggregationServiceDep = Annotated[AggregationService, Depends(get_aggregation_service)]
SubredditServiceDep = Annotated[SubredditService, Depends(get_subreddit_service)]


async def get_latest_query_run_or_404(
    query_id: str,
    query_read_service: QueryReadServiceDep,
    settings: SettingsDep,
) -> QueryRun:
    provider_name, provider_version = sentiment_provider_identity(settings)
    run = await query_read_service.get_latest_run_for_provider(
        query_id,
        provider_name,
        provider_version,
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Query not found")
    return run


async def get_query_run_or_404(
    run_id: str,
    query_read_service: QueryReadServiceDep,
) -> QueryRun:
    run = await query_read_service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Query run not found")
    return run


QueryRunDep = Annotated[QueryRun, Depends(get_query_run_or_404)]
LatestQueryRunDep = Annotated[QueryRun, Depends(get_latest_query_run_or_404)]


async def get_query_for_run_or_404(
    run: QueryRunDep,
    query_read_service: QueryReadServiceDep,
) -> Query:
    query = await query_read_service.get_query(run.query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Query not found")
    return query


QueryForRunDep = Annotated[Query, Depends(get_query_for_run_or_404)]
