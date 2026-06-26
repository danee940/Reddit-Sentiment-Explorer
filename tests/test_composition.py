from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_sentiment",
)

from unittest.mock import MagicMock, patch

from reddit_sentiment.composition import (
    _get_shared_openai_provider,
    create_aggregation_service,
    create_arctic_shift_collector,
    create_cache_service,
    create_query_pipeline_services,
    create_query_read_service,
    create_query_service,
    create_sentiment_provider,
    create_sentiment_service,
    create_sentiment_service_for_query_run,
    create_subreddit_service,
    get_app_settings,
)
from reddit_sentiment.core.config import Settings
from reddit_sentiment.sentiment.providers.mock import MockSentimentProvider
from reddit_sentiment.sentiment.providers.xlm_roberta import XLMRobertaSentimentProvider


class SessionStub:
    pass


class QueryRunStub:
    sentiment_provider_name = "mock"
    sentiment_provider_version = "heuristic-v3"


def test_get_app_settings_returns_settings_instance() -> None:
    result = get_app_settings()
    assert isinstance(result, Settings)


def test_create_query_service_returns_instance() -> None:
    session = SessionStub()
    service = create_query_service(session)  # type: ignore[arg-type]
    from reddit_sentiment.services.query_service import QueryService

    assert isinstance(service, QueryService)
    assert service.session is session


def test_create_query_service_uses_provided_settings() -> None:
    session = SessionStub()
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    service = create_query_service(session, settings=settings)  # type: ignore[arg-type]
    assert service.settings is settings


def test_create_query_read_service_returns_instance() -> None:
    session = SessionStub()
    service = create_query_read_service(session)  # type: ignore[arg-type]
    from reddit_sentiment.services.query_read_service import QueryReadService

    assert isinstance(service, QueryReadService)
    assert service.session is session


def test_create_cache_service_returns_instance() -> None:
    session = SessionStub()
    service = create_cache_service(session)  # type: ignore[arg-type]
    from reddit_sentiment.services.cache_service import CacheService

    assert isinstance(service, CacheService)


def test_create_aggregation_service_returns_instance() -> None:
    session = SessionStub()
    service = create_aggregation_service(session)  # type: ignore[arg-type]
    from reddit_sentiment.services.aggregation_service import AggregationService

    assert isinstance(service, AggregationService)
    assert service.session is session


def test_create_subreddit_service_returns_instance() -> None:
    service = create_subreddit_service()
    from reddit_sentiment.services.subreddit_service import SubredditService

    assert isinstance(service, SubredditService)


def test_create_subreddit_service_accepts_client_factory() -> None:
    factory = lambda: None  # noqa: E731
    service = create_subreddit_service(client_factory=factory)  # type: ignore[arg-type]
    from reddit_sentiment.services.subreddit_service import SubredditService

    assert isinstance(service, SubredditService)


def test_create_arctic_shift_collector_returns_instance() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    collector = create_arctic_shift_collector(settings=settings)
    from reddit_sentiment.collectors.arctic_shift.client import ArcticShiftCollector

    assert isinstance(collector, ArcticShiftCollector)


def test_create_sentiment_provider_returns_mock_by_default() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    provider, name, version, owned = create_sentiment_provider(settings=settings)
    assert isinstance(provider, MockSentimentProvider)
    assert name == "mock"
    assert owned is True


def test_create_sentiment_provider_returns_xlm_roberta() -> None:
    settings = Settings(sentiment_provider="xlm_roberta", llm_api_key="")
    provider, name, version, owned = create_sentiment_provider(settings=settings)
    assert isinstance(provider, XLMRobertaSentimentProvider)
    assert name == "xlm_roberta"
    assert owned is True


def test_create_sentiment_provider_openai_with_client_factory() -> None:
    from reddit_sentiment.sentiment.providers.openai_provider import OpenAISentimentProvider

    settings = Settings(sentiment_provider="openai", llm_api_key="test-key")
    factory = MagicMock()
    provider, name, version, owned = create_sentiment_provider(
        settings=settings, client_factory=factory
    )
    assert isinstance(provider, OpenAISentimentProvider)
    assert name == "openai"
    assert owned is True


def test_create_sentiment_provider_openai_shared_provider() -> None:
    from reddit_sentiment.sentiment.providers.openai_provider import OpenAISentimentProvider

    settings = Settings(sentiment_provider="openai", llm_api_key="test-key")
    _get_shared_openai_provider.cache_clear()
    with patch(
        "reddit_sentiment.composition.get_settings",
        return_value=settings,
    ):
        provider, name, version, owned = create_sentiment_provider(
            settings=settings, client_factory=None
        )
    assert isinstance(provider, OpenAISentimentProvider)
    assert name == "openai"
    assert owned is False


def test_create_sentiment_service_for_query_run_mock() -> None:
    session = SessionStub()
    run = QueryRunStub()
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    service = create_sentiment_service_for_query_run(
        session,  # type: ignore[arg-type]
        run,  # type: ignore[arg-type]
        settings=settings,
    )
    from reddit_sentiment.services.sentiment_service import SentimentService

    assert isinstance(service, SentimentService)
    assert isinstance(service.provider, MockSentimentProvider)


def test_create_sentiment_service_for_query_run_xlm_roberta() -> None:
    session = SessionStub()

    class XLMRunStub:
        sentiment_provider_name = "xlm_roberta"
        sentiment_provider_version = "cardiffnlp-v1"

    settings = Settings(sentiment_provider="xlm_roberta", llm_api_key="")
    service = create_sentiment_service_for_query_run(
        session,  # type: ignore[arg-type]
        XLMRunStub(),  # type: ignore[arg-type]
        settings=settings,
    )
    assert isinstance(service.provider, XLMRobertaSentimentProvider)


def test_create_sentiment_service_for_query_run_openai_with_factory() -> None:
    from reddit_sentiment.sentiment.providers.openai_provider import OpenAISentimentProvider

    session = SessionStub()

    class OpenAIRunStub:
        sentiment_provider_name = "openai"
        sentiment_provider_version = "gpt-4o-mini-v1"

    settings = Settings(sentiment_provider="openai", llm_api_key="test-key")
    factory = MagicMock()
    service = create_sentiment_service_for_query_run(
        session,  # type: ignore[arg-type]
        OpenAIRunStub(),  # type: ignore[arg-type]
        settings=settings,
        client_factory=factory,
    )
    assert isinstance(service.provider, OpenAISentimentProvider)
    assert service._owned_provider is True


def test_create_sentiment_service_for_query_run_openai_shared() -> None:
    from reddit_sentiment.sentiment.providers.openai_provider import OpenAISentimentProvider

    session = SessionStub()

    class OpenAIRunStub:
        sentiment_provider_name = "openai"
        sentiment_provider_version = "gpt-4o-mini-v1"

    settings = Settings(sentiment_provider="openai", llm_api_key="test-key")
    _get_shared_openai_provider.cache_clear()
    with patch(
        "reddit_sentiment.composition.get_settings",
        return_value=settings,
    ):
        service = create_sentiment_service_for_query_run(
            session,  # type: ignore[arg-type]
            OpenAIRunStub(),  # type: ignore[arg-type]
            settings=settings,
            client_factory=None,
        )
    assert isinstance(service.provider, OpenAISentimentProvider)
    assert service._owned_provider is False


def test_create_sentiment_service_all_auto() -> None:
    session = SessionStub()
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    service = create_sentiment_service(session, settings=settings)  # type: ignore[arg-type]
    from reddit_sentiment.services.sentiment_service import SentimentService

    assert isinstance(service, SentimentService)
    assert isinstance(service.provider, MockSentimentProvider)


def test_create_sentiment_service_with_explicit_provider() -> None:
    session = SessionStub()
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    explicit_provider = MockSentimentProvider()
    service = create_sentiment_service(
        session,  # type: ignore[arg-type]
        settings=settings,
        provider=explicit_provider,
        provider_name="mock",
        provider_version="custom-v1",
    )
    assert service.provider is explicit_provider
    assert service.provider_name == "mock"
    assert service.provider_version == "custom-v1"


def test_create_query_pipeline_services_returns_named_tuple() -> None:
    session = SessionStub()
    settings = Settings(
        sentiment_provider="mock",
        llm_api_key="",
        default_subreddits=["linux"],
    )

    class QueryRunStubFull:
        id = "run-1"
        sentiment_provider_name = "mock"
        sentiment_provider_version = "heuristic-v3"
        language_filter = "en"

    services = create_query_pipeline_services(
        session,  # type: ignore[arg-type]
        term="linux",
        query_run=QueryRunStubFull(),  # type: ignore[arg-type]
        settings=settings,
    )
    from reddit_sentiment.composition import QueryPipelineServices

    assert isinstance(services, QueryPipelineServices)
    assert services.settings is settings
