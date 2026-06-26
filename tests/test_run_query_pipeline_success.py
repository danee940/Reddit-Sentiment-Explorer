from __future__ import annotations

import asyncio
from typing import Any

from reddit_sentiment.collectors.arctic_shift.client import (
    ArcticShiftCollector,
    CollectedComment,
    CollectedPost,
)
from reddit_sentiment.composition import QueryPipelineServices
from reddit_sentiment.core.config import Settings
from reddit_sentiment.db.models import QueryRun
from reddit_sentiment.sentiment.providers.base import MOCK_PROVIDER_VERSION
from reddit_sentiment.services.aggregation_service import AggregationService
from reddit_sentiment.services.collection_persistence_service import CollectionPersistenceService
from reddit_sentiment.services.document_match_service import DocumentMatchService
from reddit_sentiment.services.language_service import LanguageService
from reddit_sentiment.services.query_service import QueryService
from reddit_sentiment.services.search_service import SearchService
from reddit_sentiment.services.sentiment_service import SentimentService


class SessionStub:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1


class FakeDocument:
    def __init__(self, doc_id: str) -> None:
        self.id = doc_id
        self.full_text = "sample content"
        self.language_filter = "en"


def test_run_query_pipeline_success_path() -> None:
    tracker: dict[str, Any] = {}
    session = SessionStub()
    fake_docs = [FakeDocument("doc-1"), FakeDocument("doc-2")]
    fake_matched_docs = [FakeDocument("doc-1")]

    class QueryServiceStub(QueryService):
        def __init__(self) -> None:
            pass

        async def mark_running(self, run: QueryRun) -> QueryRun:
            tracker["mark_running"] = True
            return run

        async def mark_completed(self, run: QueryRun) -> QueryRun:
            tracker["mark_completed"] = True
            return run

        async def mark_failed(self, run: QueryRun, error_message: str) -> QueryRun:
            tracker["mark_failed"] = error_message
            return run

        async def get_run(self, run_id: str) -> QueryRun | None:
            return QueryRun(
                id=run_id,
                query_id="query-1",
                sentiment_provider_name="mock",
                sentiment_provider_version=MOCK_PROVIDER_VERSION,
            )

    class CollectorStub(ArcticShiftCollector):
        def __init__(self) -> None:
            pass

        async def collect(
            self,
            term: str,
            subreddit_names: list[str],
            limit: int | None = None,
        ) -> tuple[list[CollectedPost], list[CollectedComment]]:
            tracker["collected"] = True
            return [], []

    class CollectionPersistenceStub(CollectionPersistenceService):
        def __init__(self) -> None:
            pass

        async def persist_posts_and_comments(
            self,
            posts: list[CollectedPost],
            comments: list[CollectedComment],
            language_filter: str,
        ) -> list[Any]:
            tracker["persisted"] = True
            return fake_docs

    class DocumentMatchStub(DocumentMatchService):
        def __init__(self) -> None:
            pass

        async def match_and_persist_batch(
            self,
            query_run: Any,
            documents: list[Any],
            search_service: Any,
        ) -> list[Any]:
            tracker["matched"] = True
            return fake_matched_docs

    class SentimentServiceStub(SentimentService):
        def __init__(self) -> None:
            pass

        async def classify_documents(self, query_run: Any, documents: list[Any]) -> list[Any]:
            tracker["classified"] = True
            return []

    class AggregationStub(AggregationService):
        def __init__(self) -> None:
            pass

        async def build(self, query_run_id: str) -> dict:
            tracker["aggregated"] = True
            return {}

    query_run = QueryRun(
        id="run-123",
        query_id="query-1",
        sentiment_provider_name="mock",
        sentiment_provider_version=MOCK_PROVIDER_VERSION,
    )
    query_run.language_filter = "en"
    query_run.scope_config = {"subreddits": ["linux"]}

    services = QueryPipelineServices(
        settings=Settings(
            default_subreddits=["linux"],
            sentiment_provider="mock",
            llm_api_key="",
        ),
        query_service=QueryServiceStub(),
        language_service=LanguageService(),
        search_service=SearchService("linux"),
        collector=CollectorStub(),
        sentiment_service=SentimentServiceStub(),
        aggregation_service=AggregationStub(),
        collection_persistence_service=CollectionPersistenceStub(),
        document_match_service=DocumentMatchStub(),
    )

    import importlib

    pipeline_module = importlib.import_module("reddit_sentiment.pipelines.run_query_pipeline")

    asyncio.run(
        pipeline_module.run_query_pipeline(
            session=session,
            query_run=query_run,
            term="linux",
            subreddit_names=["linux"],
            services=services,
        )
    )

    assert tracker.get("mark_running") is True
    assert tracker.get("collected") is True
    assert tracker.get("persisted") is True
    assert tracker.get("matched") is True
    assert tracker.get("classified") is True
    assert tracker.get("aggregated") is True
    assert tracker.get("mark_completed") is True
    assert "mark_failed" not in tracker
    assert session.commit_calls == 2
    assert session.rollback_calls == 0


def test_run_query_pipeline_failed_run_is_none_after_rollback() -> None:
    tracker: dict[str, Any] = {}
    session = SessionStub()

    class QueryServiceStub(QueryService):
        def __init__(self) -> None:
            pass

        async def mark_running(self, run: QueryRun) -> QueryRun:
            return run

        async def get_run(self, run_id: str) -> None:
            tracker["get_run_called"] = True
            return None

        async def mark_failed(self, run: QueryRun, error_message: str) -> QueryRun:
            tracker["mark_failed"] = error_message
            return run

        async def mark_completed(self, run: QueryRun) -> QueryRun:
            return run

    class FailingCollector(ArcticShiftCollector):
        def __init__(self) -> None:
            pass

        async def collect(
            self,
            term: str,
            subreddit_names: list[str],
            limit: int | None = None,
        ) -> tuple[list[CollectedPost], list[CollectedComment]]:
            raise RuntimeError("network failure")

    class SentimentServiceStub(SentimentService):
        def __init__(self) -> None:
            pass

    class AggregationStub(AggregationService):
        def __init__(self) -> None:
            pass

    class CollectionPersistenceStub(CollectionPersistenceService):
        def __init__(self) -> None:
            pass

    class DocumentMatchStub(DocumentMatchService):
        def __init__(self) -> None:
            pass

    query_run = QueryRun(
        id="run-456",
        query_id="query-1",
        sentiment_provider_name="mock",
        sentiment_provider_version=MOCK_PROVIDER_VERSION,
    )
    query_run.language_filter = "en"
    query_run.scope_config = {}

    services = QueryPipelineServices(
        settings=Settings(
            default_subreddits=["linux"],
            sentiment_provider="mock",
            llm_api_key="",
        ),
        query_service=QueryServiceStub(),
        language_service=LanguageService(),
        search_service=SearchService("linux"),
        collector=FailingCollector(),
        sentiment_service=SentimentServiceStub(),
        aggregation_service=AggregationStub(),
        collection_persistence_service=CollectionPersistenceStub(),
        document_match_service=DocumentMatchStub(),
    )

    import importlib

    pipeline_module = importlib.import_module("reddit_sentiment.pipelines.run_query_pipeline")

    asyncio.run(
        pipeline_module.run_query_pipeline(
            session=session,
            query_run=query_run,
            term="linux",
            subreddit_names=["linux"],
            services=services,
        )
    )

    assert tracker.get("get_run_called") is True
    assert "mark_failed" not in tracker
    assert session.rollback_calls == 1
