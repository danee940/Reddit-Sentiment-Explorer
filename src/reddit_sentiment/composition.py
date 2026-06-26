from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.collectors.arctic_shift.client import ArcticShiftCollector
from reddit_sentiment.core.config import Settings, get_settings
from reddit_sentiment.db.models import QueryRun
from reddit_sentiment.sentiment.provider_identity import sentiment_provider_identity
from reddit_sentiment.sentiment.providers import (
    MockSentimentProvider,
    OpenAISentimentProvider,
    XLMRobertaSentimentProvider,
)
from reddit_sentiment.sentiment.providers.base import SentimentProvider
from reddit_sentiment.services.aggregation_service import AggregationService
from reddit_sentiment.services.cache_service import CacheService
from reddit_sentiment.services.collection_persistence_service import CollectionPersistenceService
from reddit_sentiment.services.document_match_service import DocumentMatchService
from reddit_sentiment.services.language_service import LanguageService
from reddit_sentiment.services.query_read_service import QueryReadService
from reddit_sentiment.services.query_service import QueryService
from reddit_sentiment.services.search_service import SearchService
from reddit_sentiment.services.sentiment_service import SentimentService
from reddit_sentiment.services.subreddit_service import SubredditService

AsyncClientFactory = Callable[..., httpx.AsyncClient]


@lru_cache(maxsize=1)
def _get_shared_openai_provider() -> OpenAISentimentProvider:
    return OpenAISentimentProvider(get_settings())


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
) -> tuple[SentimentProvider, str, str, bool]:
    active_settings = settings or get_settings()
    name, version = sentiment_provider_identity(active_settings)
    if name == "openai":
        if client_factory is None:
            return _get_shared_openai_provider(), name, version, False
        return OpenAISentimentProvider(active_settings, client_factory), name, version, True
    if name == "xlm_roberta":
        return XLMRobertaSentimentProvider(), name, version, True
    return MockSentimentProvider(), name, version, True


def create_sentiment_service_for_query_run(
    session: AsyncSession,
    query_run: QueryRun,
    settings: Settings | None = None,
    client_factory: AsyncClientFactory | None = None,
) -> SentimentService:
    active_settings = settings or get_settings()
    name = query_run.sentiment_provider_name
    version = query_run.sentiment_provider_version
    owned = True
    if name == "openai":
        if client_factory is None:
            provider: SentimentProvider = _get_shared_openai_provider()
            owned = False
        else:
            provider = OpenAISentimentProvider(active_settings, client_factory)
    elif name == "xlm_roberta":
        provider = XLMRobertaSentimentProvider()
    else:
        provider = MockSentimentProvider()
    return SentimentService(
        session,
        settings=active_settings,
        provider=provider,
        provider_name=name,
        provider_version=version,
        owned_provider=owned,
    )


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
    owned = True
    if active_provider is None or active_provider_name is None or active_provider_version is None:
        (
            built_provider,
            built_provider_name,
            built_provider_version,
            built_owned,
        ) = create_sentiment_provider(active_settings, client_factory)
        if active_provider is None:
            active_provider = built_provider
            owned = built_owned
        active_provider_name = active_provider_name or built_provider_name
        active_provider_version = active_provider_version or built_provider_version
    return SentimentService(
        session,
        settings=active_settings,
        provider=active_provider,
        provider_name=active_provider_name,
        provider_version=active_provider_version,
        owned_provider=owned,
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
    query_run: QueryRun,
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
        sentiment_service=create_sentiment_service_for_query_run(
            session,
            query_run,
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
