import asyncio
import importlib

import pytest

from reddit_sentiment.collectors.arctic_shift.client import (
    ArcticShiftCollector,
    CollectedComment,
    CollectedPost,
)
from reddit_sentiment.composition import QueryPipelineServices
from reddit_sentiment.core.config import Settings
from reddit_sentiment.db.models import QueryRun
from reddit_sentiment.services.aggregation_service import AggregationService
from reddit_sentiment.services.collection_persistence_service import CollectionPersistenceService
from reddit_sentiment.services.document_match_service import DocumentMatchService
from reddit_sentiment.services.language_service import LanguageService
from reddit_sentiment.services.query_service import QueryService
from reddit_sentiment.services.search_service import SearchService
from reddit_sentiment.services.sentiment_service import SentimentService

pipeline_module = importlib.import_module("reddit_sentiment.pipelines.run_query_pipeline")


class QueryRunStub:
    def __init__(self) -> None:
        self._id = "run-123"
        self.id_accessible = True
        self.language_filter = "hu"

    @property
    def id(self) -> str:
        if not self.id_accessible:
            raise RuntimeError("query run id should not be read after rollback")
        return self._id


class SessionStub:
    def __init__(self, query_run: QueryRunStub) -> None:
        self.query_run = query_run
        self.rollback_calls = 0
        self.commit_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1
        self.query_run.id_accessible = False

    async def commit(self) -> None:
        self.commit_calls += 1


def test_run_query_pipeline_marks_failure_with_stable_run_id() -> None:
    tracker: dict[str, object] = {}

    class QueryServiceStub(QueryService):
        def __init__(self) -> None:
            pass

        async def mark_running(self, run: QueryRun) -> QueryRun:
            tracker["mark_running_run"] = run
            return run

        async def get_run(self, run_id: str) -> QueryRun | None:
            tracker["get_run_id"] = run_id
            return QueryRun(id=run_id, query_id="query-1")

        async def mark_failed(self, run: QueryRun, error_message: str) -> QueryRun:
            tracker["mark_failed_run_id"] = run.id
            tracker["mark_failed_error"] = error_message
            return run

    class CollectorStub(ArcticShiftCollector):
        def __init__(self) -> None:
            pass

        async def collect(
            self,
            term: str,
            subreddit_names: list[str],
            limit: int | None = None,
        ) -> tuple[list[CollectedPost], list[CollectedComment]]:
            raise RuntimeError("collector exploded")

    class SentimentServiceStub(SentimentService):
        def __init__(self) -> None:
            pass

    class AggregationServiceStub(AggregationService):
        def __init__(self) -> None:
            pass

    class CollectionPersistenceServiceStub(CollectionPersistenceService):
        def __init__(self) -> None:
            pass

    class DocumentMatchServiceStub(DocumentMatchService):
        def __init__(self) -> None:
            pass

    query_run = QueryRunStub()
    session = SessionStub(query_run)
    services = QueryPipelineServices(
        settings=Settings(default_subreddits=["hungary"], llm_provider="mock", llm_api_key=""),
        query_service=QueryServiceStub(),
        language_service=LanguageService(),
        search_service=SearchService("Tisza"),
        collector=CollectorStub(),
        sentiment_service=SentimentServiceStub(),
        aggregation_service=AggregationServiceStub(),
        collection_persistence_service=CollectionPersistenceServiceStub(),
        document_match_service=DocumentMatchServiceStub(),
    )

    with pytest.raises(RuntimeError, match="collector exploded"):
        asyncio.run(
            pipeline_module.run_query_pipeline(
                session=session,
                query_run=query_run,
                term="Tisza",
                subreddit_names=["hungary"],
                services=services,
            )
        )

    assert tracker["get_run_id"] == "run-123"
    assert tracker["mark_failed_run_id"] == "run-123"
    assert tracker["mark_failed_error"] == "collector exploded"
    assert session.rollback_calls == 1
    assert session.commit_calls == 2
