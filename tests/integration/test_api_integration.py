from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reddit_sentiment.core.config import get_settings

pytestmark = pytest.mark.integration


def test_health_returns_ok(app) -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_create_query_returns_pending_run(app) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/queries",
            json={
                "term": "integration test term",
                "subreddits": ["hungary", "budapest"],
                "content_language": "en",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["is_cached"] is False
    assert body["query_id"]
    assert body["query_run_id"]
    assert body["query_id"] != body["query_run_id"]


def test_get_latest_query_run_after_create(app) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/queries",
            json={
                "term": "latest run lookup",
                "subreddits": ["hungary"],
                "content_language": "hu",
            },
        ).json()
        query_id = created["query_id"]
        latest = client.get(f"/queries/{query_id}")
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["id"] == created["query_run_id"]
    assert payload["query_id"] == query_id
    assert payload["status"] == "pending"
    assert payload["language_filter"] == "hu"


def test_same_normalized_term_reuses_query_id(app) -> None:
    with TestClient(app) as client:
        first = client.post(
            "/queries",
            json={
                "term": "  Shared Term  ",
                "subreddits": ["hungary"],
                "content_language": "en",
            },
        ).json()
        second = client.post(
            "/queries",
            json={
                "term": "shared term",
                "subreddits": ["hungary"],
                "content_language": "en",
            },
        ).json()
    assert first["query_id"] == second["query_id"]
    assert first["query_run_id"] != second["query_run_id"]


def test_refresh_query_run_creates_new_pending_run(app) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/queries",
            json={
                "term": "refresh flow",
                "subreddits": ["hungary"],
                "content_language": "en",
            },
        ).json()
        run_id = created["query_run_id"]
        refreshed = client.post(f"/query-runs/{run_id}/refresh")
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["query_id"] == created["query_id"]
    assert body["query_run_id"] != run_id
    assert body["status"] == "pending"
    assert body["is_cached"] is False


def test_ready_returns_ready(app) -> None:
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_get_query_run_by_id(app) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/queries",
            json={"term": "run by id", "subreddits": ["hungary"], "content_language": "en"},
        ).json()
        run_id = created["query_run_id"]
        run = client.get(f"/query-runs/{run_id}")
    assert run.status_code == 200
    payload = run.json()
    assert payload["id"] == run_id
    assert payload["query_id"] == created["query_id"]
    assert payload["status"] == "pending"


def test_create_query_returns_cached_run(app, complete_run) -> None:
    scope = {"term": "cached query", "subreddits": ["hungary"], "content_language": "en"}
    with TestClient(app) as client:
        first = client.post("/queries", json=scope).json()
    complete_run(first["query_run_id"])
    with TestClient(app) as client:
        second = client.post("/queries", json=scope).json()
    assert second["is_cached"] is True
    assert second["query_run_id"] == first["query_run_id"]
    assert second["query_id"] == first["query_id"]


def test_create_query_skips_cache_when_sentiment_provider_changes(
    app, complete_run, monkeypatch: pytest.MonkeyPatch
) -> None:
    scope = {
        "term": "provider cache isolation",
        "subreddits": ["hungary"],
        "content_language": "en",
    }
    with TestClient(app) as client:
        first = client.post("/queries", json=scope).json()
    complete_run(first["query_run_id"])
    monkeypatch.setenv("SENTIMENT_PROVIDER", "xlm_roberta")
    get_settings.cache_clear()
    with TestClient(app) as client:
        second = client.post("/queries", json=scope).json()
    assert second["is_cached"] is False
    assert second["query_run_id"] != first["query_run_id"]
    assert second["query_id"] == first["query_id"]
    assert second["sentiment_provider_name"] == "xlm_roberta"
    get_settings.cache_clear()


def test_get_unknown_query_returns_404(app) -> None:
    with TestClient(app) as client:
        response = client.get("/queries/does-not-exist")
    assert response.status_code == 404


def test_get_unknown_run_returns_404(app) -> None:
    with TestClient(app) as client:
        response = client.get("/query-runs/does-not-exist")
    assert response.status_code == 404


def test_refresh_unknown_run_returns_404(app) -> None:
    with TestClient(app) as client:
        response = client.post("/query-runs/does-not-exist/refresh")
    assert response.status_code == 404


def test_get_charts_returns_empty_payload(app) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/queries",
            json={"term": "charts test", "subreddits": ["hungary"], "content_language": "en"},
        ).json()
        charts = client.get(f"/query-runs/{created['query_run_id']}/charts")
    assert charts.status_code == 200
    payload = charts.json()
    assert payload["overview"] == {}
    assert payload["sentiment_distribution"] == []
    assert payload["sentiment_timeline"] == []
    assert payload["volume_timeline"] == []
    assert payload["subreddit_breakdown"] == []


def test_get_documents_returns_empty_list(app) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/queries",
            json={"term": "documents test", "subreddits": ["hungary"], "content_language": "en"},
        ).json()
        docs = client.get(f"/query-runs/{created['query_run_id']}/documents")
    assert docs.status_code == 200
    assert docs.json()["items"] == []


def test_create_query_uses_default_subreddits_when_omitted(app, fetch_run) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/queries",
            json={"term": "default subreddits test", "content_language": "en"},
        )
    assert response.status_code == 200
    run = fetch_run(response.json()["query_run_id"])
    assert run is not None
    assert sorted(run.scope_config["subreddits"]) == ["askhungary", "budapest", "hu", "hungary"]
