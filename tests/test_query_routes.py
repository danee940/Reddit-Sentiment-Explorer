from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from reddit_sentiment.api import dependencies as api_dependencies
from reddit_sentiment.api import main as api_main
from reddit_sentiment.api.routes import query_routes
from reddit_sentiment.api.schemas.query import QueryCreateRequest
from reddit_sentiment.core.config import Settings
from reddit_sentiment.core.enums import QueryRunStatus, SentimentLabel
from reddit_sentiment.sentiment.providers.base import MOCK_PROVIDER_VERSION
from reddit_sentiment.services.query_read_service import QueryRunDocument


@pytest.fixture
def app(monkeypatch):
    async def fake_initialize_database() -> None:
        return None

    monkeypatch.setattr(api_main, "initialize_database", fake_initialize_database)
    app = api_main.create_app()
    yield app
    app.dependency_overrides.clear()


def test_build_scope_config_uses_request_subreddits() -> None:
    request = QueryCreateRequest(term="Big Mac", subreddits=["budapest", "hungary", "budapest"])
    settings = Settings(default_subreddits=["hungary", "askhungary"])

    assert query_routes.build_scope_config(request, settings) == {
        "subreddits": ["budapest", "hungary"]
    }


def test_build_scope_config_uses_defaults_when_request_list_is_empty() -> None:
    request = QueryCreateRequest(term="Big Mac", subreddits=[])
    settings = Settings(default_subreddits=["hungary", "askhungary"])

    assert query_routes.build_scope_config(request, settings) == {
        "subreddits": ["askhungary", "hungary"]
    }


def test_query_request_normalizes_content_language() -> None:
    request = QueryCreateRequest(term="Big Mac", content_language="RU-RU")

    assert request.content_language == "ru"


def test_create_query_uses_dependency_overrides_for_cached_run(app) -> None:
    class QueryServiceStub:
        async def get_or_create_query(self, term: str):
            assert term == "Big Mac"
            return SimpleNamespace(id="query-1")

    class CacheServiceStub:
        async def get_fresh_run(
            self,
            query_id: str,
            scope_config: dict,
            language_filter: str,
            sentiment_provider_name: str,
            sentiment_provider_version: str,
        ):
            assert query_id == "query-1"
            assert scope_config == {"subreddits": ["budapest", "hungary"]}
            assert language_filter == "hu"
            assert sentiment_provider_name == "mock"
            assert sentiment_provider_version == MOCK_PROVIDER_VERSION
            return SimpleNamespace(
                id="run-1",
                status=QueryRunStatus.completed,
                sentiment_provider_name="mock",
                sentiment_provider_version=MOCK_PROVIDER_VERSION,
            )

    app.dependency_overrides[api_dependencies.get_app_settings] = lambda: SimpleNamespace(
        default_subreddits=["hungary", "askhungary"],
        sentiment_provider="mock",
        llm_api_key="",
        llm_model="gpt-4o-mini",
    )
    app.dependency_overrides[api_dependencies.get_query_service] = lambda: QueryServiceStub()
    app.dependency_overrides[api_dependencies.get_cache_service] = lambda: CacheServiceStub()

    with TestClient(app) as client:
        response = client.post(
            "/queries",
            json={
                "term": "Big Mac",
                "subreddits": ["budapest", "hungary", "budapest"],
                "content_language": "hu-HU",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "query_id": "query-1",
        "query_run_id": "run-1",
        "status": "completed",
        "is_cached": True,
        "sentiment_provider_name": "mock",
        "sentiment_provider_version": MOCK_PROVIDER_VERSION,
    }


def test_get_query_run_documents_uses_query_read_service_dependency(app) -> None:
    created_utc = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)

    class QueryReadServiceStub:
        async def get_run_documents(self, run_id: str) -> list[QueryRunDocument]:
            assert run_id == "run-1"
            return [
                QueryRunDocument(
                    document_id="doc-1",
                    source_type="post",
                    subreddit="hungary",
                    created_utc=created_utc,
                    score=42,
                    snippet="Example snippet",
                    content="Example snippet and more",
                    sentiment_label=SentimentLabel.positive,
                    sentiment_score=1,
                    sentiment_confidence=0.9,
                    sentiment_rationale="Positive wording",
                    sentiment_evidence_phrases=["good value"],
                    permalink="https://reddit.com/r/hungary/comments/abc",
                )
            ]

    app.dependency_overrides[api_dependencies.get_query_run_or_404] = lambda: SimpleNamespace(
        id="run-1"
    )
    app.dependency_overrides[api_dependencies.get_query_read_service] = (
        lambda: QueryReadServiceStub()
    )

    with TestClient(app) as client:
        response = client.get("/query-runs/run-1/documents")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "document_id": "doc-1",
                "source_type": "post",
                "subreddit": "hungary",
                "created_utc": "2025-01-02T03:04:05Z",
                "score": 42,
                "snippet": "Example snippet",
                "content": "Example snippet and more",
                "sentiment_label": "positive",
                "sentiment_score": 1,
                "sentiment_confidence": 0.9,
                "sentiment_rationale": "Positive wording",
                "sentiment_evidence_phrases": ["good value"],
                "permalink": "https://reddit.com/r/hungary/comments/abc",
            }
        ]
    }


def test_refresh_query_run_uses_run_and_query_dependencies(app) -> None:
    class QueryServiceStub:
        async def create_run(self, query_id: str, scope_config: dict, language_filter: str):
            assert query_id == "query-1"
            assert scope_config == {"subreddits": ["hungary"]}
            assert language_filter == "hu"
            return SimpleNamespace(
                id="run-2",
                status=QueryRunStatus.pending,
                sentiment_provider_name="mock",
                sentiment_provider_version=MOCK_PROVIDER_VERSION,
            )

    app.dependency_overrides[api_dependencies.get_query_run_or_404] = lambda: SimpleNamespace(
        id="run-1",
        query_id="query-1",
        scope_config={"subreddits": ["hungary"]},
        language_filter="hu",
    )
    app.dependency_overrides[api_dependencies.get_query_for_run_or_404] = (
        lambda: SimpleNamespace(id="query-1")
    )
    app.dependency_overrides[api_dependencies.get_query_service] = lambda: QueryServiceStub()

    with TestClient(app) as client:
        response = client.post("/query-runs/run-1/refresh")

    assert response.status_code == 200
    assert response.json() == {
        "query_id": "query-1",
        "query_run_id": "run-2",
        "status": "pending",
        "is_cached": False,
        "sentiment_provider_name": "mock",
        "sentiment_provider_version": MOCK_PROVIDER_VERSION,
    }
