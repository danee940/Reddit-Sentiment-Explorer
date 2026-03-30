from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from reddit_sentiment.api.dependencies import (
    AggregationServiceDep,
    CacheServiceDep,
    DBSession,
    LatestQueryRunDep,
    QueryForRunDep,
    QueryReadServiceDep,
    QueryRunDep,
    QueryServiceDep,
    SettingsDep,
)
from reddit_sentiment.api.schemas.query import (
    ChartPayload,
    DocumentResponse,
    DocumentsResponse,
    QueryCreateRequest,
    QueryResponse,
    QueryRunResponse,
)
from reddit_sentiment.core.config import Settings
from reddit_sentiment.sentiment.provider_identity import sentiment_provider_identity
from reddit_sentiment.services.subreddit_service import SubredditService

router = APIRouter()


def build_scope_config(request: QueryCreateRequest, settings: Settings) -> dict:
    subreddits = request.subreddits or list(settings.default_subreddits)
    normalized_subreddits = SubredditService.normalize_names(subreddits)
    return {"subreddits": sorted(normalized_subreddits)}


@router.post("/queries", response_model=QueryResponse)
async def create_query(
    request: QueryCreateRequest,
    settings: SettingsDep,
    query_service: QueryServiceDep,
    cache_service: CacheServiceDep,
) -> QueryResponse:
    query = await query_service.get_or_create_query(request.term)
    scope_config = build_scope_config(request, settings)
    provider_name, provider_version = sentiment_provider_identity(settings)
    cached_run = await cache_service.get_fresh_run(
        query.id,
        scope_config,
        request.content_language,
        provider_name,
        provider_version,
    )
    if cached_run is not None:
        return QueryResponse(
            query_id=query.id,
            query_run_id=cached_run.id,
            status=cached_run.status,
            is_cached=True,
            sentiment_provider_name=cached_run.sentiment_provider_name,
            sentiment_provider_version=cached_run.sentiment_provider_version,
        )

    run = await query_service.create_run(
        query_id=query.id,
        scope_config=scope_config,
        language_filter=request.content_language,
    )
    return QueryResponse(
        query_id=query.id,
        query_run_id=run.id,
        status=run.status,
        is_cached=False,
        sentiment_provider_name=run.sentiment_provider_name,
        sentiment_provider_version=run.sentiment_provider_version,
    )


@router.get("/queries/{query_id}", response_model=QueryRunResponse)
async def get_latest_query_run(run: LatestQueryRunDep) -> QueryRunResponse:
    return QueryRunResponse.model_validate(run, from_attributes=True)


@router.get("/query-runs/{run_id}", response_model=QueryRunResponse)
async def get_query_run(run: QueryRunDep) -> QueryRunResponse:
    return QueryRunResponse.model_validate(run, from_attributes=True)


@router.get("/query-runs/{run_id}/charts", response_model=ChartPayload)
async def get_query_run_charts(
    run: QueryRunDep,
    aggregation_service: AggregationServiceDep,
) -> ChartPayload:
    payload = await aggregation_service.get_payload(run.id)
    return ChartPayload.model_validate(payload)


@router.get("/query-runs/{run_id}/documents", response_model=DocumentsResponse)
async def get_query_run_documents(
    run: QueryRunDep,
    query_read_service: QueryReadServiceDep,
) -> DocumentsResponse:
    documents = await query_read_service.get_run_documents(run.id)
    items = [
        DocumentResponse.model_validate(document, from_attributes=True) for document in documents
    ]
    return DocumentsResponse(items=items)


@router.post("/query-runs/{run_id}/refresh", response_model=QueryResponse)
async def refresh_query_run(
    run: QueryRunDep,
    query: QueryForRunDep,
    query_service: QueryServiceDep,
) -> QueryResponse:
    new_run = await query_service.create_run(
        query_id=query.id,
        scope_config=run.scope_config,
        language_filter=run.language_filter,
    )
    return QueryResponse(
        query_id=query.id,
        query_run_id=new_run.id,
        status=new_run.status,
        is_cached=False,
        sentiment_provider_name=new_run.sentiment_provider_name,
        sentiment_provider_version=new_run.sentiment_provider_version,
    )


@router.get("/health")
async def health(session: DBSession) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@router.get("/ready")
async def ready(session: DBSession) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
