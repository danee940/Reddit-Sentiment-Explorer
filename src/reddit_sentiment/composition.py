from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.collectors.arctic_shift.client import ArcticShiftCollector
from reddit_sentiment.core.config import Settings, get_settings
from reddit_sentiment.sentiment.providers import MockSentimentProvider, OpenAISentimentProvider
from reddit_sentiment.sentiment.providers.base import (
    MOCK_PROVIDER_VERSION,
    SentimentProvider,
    get_openai_provider_version,
)
from reddit_sentiment.services.aggregation_service import AggregationService
from reddit_sentiment.services.cache_service import CacheService
from reddit_sentiment.services.collection_persistence_service import (
    CollectionPersistenceService,
)
from reddit_sentiment.services.document_match_service import DocumentMatchService
from reddit_sentiment.services.language_service import LanguageService
from reddit_sentiment.services.query_read_service import QueryReadService
from reddit_sentiment.services.query_service import QueryService
from reddit_sentiment.services.search_service import SearchService
from reddit_sentiment.services.sentiment_service import SentimentService
from reddit_sentiment.services.subreddit_service import SubredditService

AsyncClientFactory = Callable[..., httpx.AsyncClient]


@dataclass(slots=True)
class QueryPipelineServices:
    settings: Settings
    query_service: QueryService
    language_service: LanguageService
    search_service: SearchService
    collector: ArcticShiftCollector
    sentiment_service: SentimentService
    aggregation_service: AggregationService
    collection_persistence_service: CollectionPersistenceService
    document_match_service: DocumentMatchService


def get_app_settings() -> Settings:
    return get_settings()


def create_query_service(session: AsyncSession, settings: Settings | None = None) -> QueryService:
    active_settings = settings or get_settings()
    return QueryService(session, settings=active_settings)


def create_query_read_service(session: AsyncSession) -> QueryReadService:
    return QueryReadService(session)


def create_cache_service(session: AsyncSession) -> CacheService:
    return CacheService(session)


def create_aggregation_service(session: AsyncSession) -> AggregationService:
    return AggregationService(session)


def create_subreddit_service(
    client_factory: AsyncClientFactory | None = None,
) -> SubredditService:
    return SubredditService(client_factory=client_factory)


def create_sentiment_provider(
    settings: Settings | None = None,
    client_factory: AsyncClientFactory | None = None,
) -> tuple[SentimentProvider, str, str]:
    active_settings = settings or get_settings()
    if active_settings.llm_provider == "openai" and active_settings.llm_api_key:
        return (
            OpenAISentimentProvider(active_settings, client_factory),
            "openai",
            get_openai_provider_version(active_settings.llm_model),
        )
    return MockSentimentProvider(), "mock", MOCK_PROVIDER_VERSION


def create_sentiment_service(
    session: AsyncSession,
    settings: Settings | None = None,
    provider: SentimentProvider | None = None,
    provider_name: str | None = None,
    provider_version: str | None = None,
    client_factory: AsyncClientFactory | None = None,
) -> SentimentService:
    active_settings = settings or get_settings()
    active_provider = provider
    active_provider_name = provider_name
    active_provider_version = provider_version
    if active_provider is None or active_provider_name is None or active_provider_version is None:
        (
            built_provider,
            built_provider_name,
            built_provider_version,
        ) = create_sentiment_provider(active_settings, client_factory)
        active_provider = active_provider or built_provider
        active_provider_name = active_provider_name or built_provider_name
        active_provider_version = active_provider_version or built_provider_version
    return SentimentService(
        session,
        settings=active_settings,
        provider=active_provider,
        provider_name=active_provider_name,
        provider_version=active_provider_version,
    )


def create_arctic_shift_collector(
    settings: Settings | None = None,
    client_factory: AsyncClientFactory | None = None,
) -> ArcticShiftCollector:
    active_settings = settings or get_settings()
    return ArcticShiftCollector(active_settings, client_factory)


def create_query_pipeline_services(
    session: AsyncSession,
    term: str,
    settings: Settings | None = None,
    collector_client_factory: AsyncClientFactory | None = None,
    provider_client_factory: AsyncClientFactory | None = None,
) -> QueryPipelineServices:
    active_settings = settings or get_settings()
    language_service = LanguageService()
    search_service = SearchService(term)
    default_subreddits = set(active_settings.default_subreddits)
    return QueryPipelineServices(
        settings=active_settings,
        query_service=create_query_service(session, active_settings),
        language_service=language_service,
        search_service=search_service,
        collector=create_arctic_shift_collector(active_settings, collector_client_factory),
        sentiment_service=create_sentiment_service(
            session,
            settings=active_settings,
            client_factory=provider_client_factory,
        ),
        aggregation_service=create_aggregation_service(session),
        collection_persistence_service=CollectionPersistenceService(
            session,
            language_service,
            search_service,
            default_subreddits,
        ),
        document_match_service=DocumentMatchService(session),
    )
