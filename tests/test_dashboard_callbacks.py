from __future__ import annotations

from types import SimpleNamespace

from dash import no_update

from reddit_sentiment.dashboard.callbacks import documents as documents_callbacks
from reddit_sentiment.dashboard.callbacks import query as query_callbacks


def test_create_query_sends_content_language_separately_from_ui_language(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    def fake_api_request(method: str, path: str, payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update({"method": method, "path": path, **payload})
        return {
            "query_id": "query-1",
            "query_run_id": "run-1",
            "status": "pending",
            "is_cached": False,
        }

    monkeypatch.setattr(query_callbacks, "api_request", fake_api_request)
    monkeypatch.setattr(
        query_callbacks,
        "settings",
        SimpleNamespace(default_subreddits=["hungary"]),
    )

    store_data, message, message_class, poll_disabled = query_callbacks.create_query(
        1,
        None,
        "en",
        "borscht",
        ["AskARussian"],
        "ru",
    )

    assert captured_payload == {
        "method": "POST",
        "path": "/queries",
        "term": "borscht",
        "subreddits": ["AskARussian"],
        "content_language": "ru",
    }
    assert store_data is not None
    assert store_data["content_language"] == "ru"
    assert message == "Query started: run-1"
    assert poll_disabled is False
    assert message_class == "mt-4 text-sm font-medium text-gray-600"


def test_create_query_with_empty_term_returns_error_message(monkeypatch) -> None:
    monkeypatch.setattr(query_callbacks, "api_request", lambda *a, **kw: {})
    store_data, message, _, poll_disabled = query_callbacks.create_query(
        1, None, "en", None, ["hungary"], "en"
    )
    assert store_data is None
    assert message == "Enter a search term."
    assert poll_disabled is True


def test_create_query_with_api_error_returns_error_message(monkeypatch) -> None:
    monkeypatch.setattr(
        query_callbacks, "api_request", lambda *a, **kw: {"error": "server unavailable"}
    )
    monkeypatch.setattr(
        query_callbacks, "settings", SimpleNamespace(default_subreddits=["hungary"])
    )
    store_data, message, _, poll_disabled = query_callbacks.create_query(
        1, None, "en", "test term", ["hungary"], "en"
    )
    assert store_data is None
    assert "server unavailable" in message
    assert poll_disabled is True


def test_poll_query_run_with_no_store_data_stops_polling(monkeypatch) -> None:
    monkeypatch.setattr(query_callbacks, "api_request", lambda *a, **kw: {})
    _, message, _, poll_disabled = query_callbacks.poll_query_run(1, "en", None)
    assert message == "No active query."
    assert poll_disabled is True


def test_poll_query_run_with_api_error_stops_polling(monkeypatch) -> None:
    store_data = {"query_run_id": "run-1", "status": "pending"}
    monkeypatch.setattr(
        query_callbacks, "api_request", lambda *a, **kw: {"error": "connection refused"}
    )
    updated_store, message, _, poll_disabled = query_callbacks.poll_query_run(1, "en", store_data)
    assert updated_store == store_data
    assert isinstance(message, str)
    assert "connection refused" in message
    assert poll_disabled is True


def test_poll_query_run_with_unchanged_status_returns_no_update(monkeypatch) -> None:
    store_data = {"query_run_id": "run-1", "status": "running"}
    monkeypatch.setattr(query_callbacks, "api_request", lambda *a, **kw: {"status": "running"})
    updated_store, message, message_class, poll_disabled = query_callbacks.poll_query_run(
        1, "en", store_data
    )
    assert updated_store is no_update
    assert message is no_update
    assert message_class is no_update
    assert poll_disabled is False


def test_poll_query_run_when_completed_stops_polling(monkeypatch) -> None:
    store_data = {"query_run_id": "run-1", "status": "pending"}
    monkeypatch.setattr(query_callbacks, "api_request", lambda *a, **kw: {"status": "completed"})
    updated_store, message, _, poll_disabled = query_callbacks.poll_query_run(1, "en", store_data)
    assert isinstance(updated_store, dict)
    assert updated_store["status"] == "completed"
    assert message == "Query completed."
    assert poll_disabled is True


def test_poll_query_run_when_failed_stops_polling(monkeypatch) -> None:
    store_data = {"query_run_id": "run-1", "status": "running"}
    monkeypatch.setattr(
        query_callbacks,
        "api_request",
        lambda *a, **kw: {"status": "failed", "error_message": "upstream timeout"},
    )
    updated_store, message, _, poll_disabled = query_callbacks.poll_query_run(1, "en", store_data)
    assert isinstance(updated_store, dict)
    assert updated_store["status"] == "failed"
    assert isinstance(message, str)
    assert "upstream timeout" in message
    assert poll_disabled is True


def test_poll_query_run_when_running_continues_polling(monkeypatch) -> None:
    store_data = {"query_run_id": "run-1", "status": "pending"}
    monkeypatch.setattr(query_callbacks, "api_request", lambda *a, **kw: {"status": "running"})
    updated_store, _, _, poll_disabled = query_callbacks.poll_query_run(1, "en", store_data)
    assert isinstance(updated_store, dict)
    assert updated_store["status"] == "running"
    assert poll_disabled is False


def test_update_history_store_adds_new_entry() -> None:
    store_data = {"query_run_id": "run-1", "query_id": "q-1", "term": "test", "status": "pending"}
    result = query_callbacks.update_history_store(store_data, [])
    assert len(result) == 1
    assert result[0]["query_run_id"] == "run-1"
    assert result[0]["term"] == "test"


def test_update_history_store_updates_existing_entry() -> None:
    existing = [
        {
            "query_run_id": "run-1",
            "term": "test",
            "status": "pending",
            "saved_at": "2024-01-01T10:00:00",
        }
    ]
    store_data = {"query_run_id": "run-1", "term": "test", "status": "completed"}
    result = query_callbacks.update_history_store(store_data, existing)
    assert len(result) == 1
    assert result[0]["status"] == "completed"
    assert result[0]["saved_at"] == "2024-01-01T10:00:00"


def test_update_history_store_caps_at_twelve_items() -> None:
    existing = [
        {
            "query_run_id": f"run-{i}",
            "term": f"t{i}",
            "status": "completed",
            "saved_at": f"2024-01-{i + 1:02d}T00:00:00",
        }
        for i in range(12)
    ]
    store_data = {
        "query_run_id": "run-new",
        "term": "new term",
        "status": "pending",
        "saved_at": "2025-01-01T00:00:00",
    }
    result = query_callbacks.update_history_store(store_data, existing)
    assert len(result) == 12


def test_update_history_store_returns_existing_when_no_store_data() -> None:
    existing = [{"query_run_id": "run-1", "term": "test", "status": "completed"}]
    assert query_callbacks.update_history_store(None, existing) == existing


def _make_document(**kwargs) -> dict:
    base: dict = {
        "id": "doc-1",
        "subreddit": "hungary",
        "sentiment_label": "positive",
        "source_type": "post",
        "date_bucket": "2024-01-01",
        "snippet_preview": "hello world",
        "content": "full content here",
    }
    return {**base, **kwargs}


def test_filter_document_rows_returns_empty_for_no_items() -> None:
    rows, selected, _ = documents_callbacks.filter_document_rows(
        [], None, None, None, None, None, "en"
    )
    assert rows == []
    assert selected == []


def test_filter_document_rows_no_filters_returns_all() -> None:
    items = [_make_document(id="a"), _make_document(id="b", subreddit="budapest")]
    rows, _, _ = documents_callbacks.filter_document_rows(
        items, None, None, None, None, None, "en"
    )
    assert len(rows) == 2


def test_filter_document_rows_by_subreddit() -> None:
    items = [
        _make_document(id="a", subreddit="hungary"),
        _make_document(id="b", subreddit="budapest"),
    ]
    rows, _, _ = documents_callbacks.filter_document_rows(
        items, None, "hungary", None, None, None, "en"
    )
    assert len(rows) == 1
    assert rows[0]["subreddit"] == "hungary"


def test_filter_document_rows_by_sentiment_label() -> None:
    items = [
        _make_document(id="a", sentiment_label="positive"),
        _make_document(id="b", sentiment_label="negative"),
    ]
    rows, _, _ = documents_callbacks.filter_document_rows(
        items, None, None, "positive", None, None, "en"
    )
    assert len(rows) == 1
    assert rows[0]["sentiment_label"] == "positive"


def test_filter_document_rows_by_source_type() -> None:
    items = [
        _make_document(id="a", source_type="post"),
        _make_document(id="b", source_type="comment"),
    ]
    rows, _, _ = documents_callbacks.filter_document_rows(
        items, None, None, None, "post", None, "en"
    )
    assert len(rows) == 1
    assert rows[0]["source_type"] == "post"


def test_filter_document_rows_by_date_bucket() -> None:
    items = [
        _make_document(id="a", date_bucket="2024-01-01"),
        _make_document(id="b", date_bucket="2024-01-02"),
    ]
    rows, _, _ = documents_callbacks.filter_document_rows(
        items, "2024-01-01", None, None, None, None, "en"
    )
    assert len(rows) == 1
    assert rows[0]["date_bucket"] == "2024-01-01"


def test_filter_document_rows_by_text_search() -> None:
    items = [
        _make_document(id="a", snippet_preview="Budapest travel tips"),
        _make_document(id="b", snippet_preview="cooking pasta at home"),
    ]
    rows, _, _ = documents_callbacks.filter_document_rows(
        items, None, None, None, None, "travel", "en"
    )
    assert len(rows) == 1


def test_filter_document_rows_selects_first_matching_id() -> None:
    items = [_make_document(id="doc-alpha"), _make_document(id="doc-beta", subreddit="budapest")]
    _, selected, _ = documents_callbacks.filter_document_rows(
        items, None, None, None, None, None, "en"
    )
    assert selected == ["doc-alpha"]
