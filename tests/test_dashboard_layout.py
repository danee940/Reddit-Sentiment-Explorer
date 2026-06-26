from __future__ import annotations

from dash import html

from reddit_sentiment.dashboard.components.layout import build_search_history, build_subreddit_list


def test_build_subreddit_list_empty_shows_env_defaults() -> None:
    result = build_subreddit_list(None, None, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert (
        "using_env_defaults" in json_str
        or "env" in json_str.lower()
        or "default" in json_str.lower()
    )


def test_build_subreddit_list_with_names_shows_remove_buttons() -> None:
    result = build_subreddit_list(["hungary"], None, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "remove-subreddit" in json_str
    assert "hungary" in json_str


def test_build_subreddit_list_with_validation_exists_true_shows_exists_badge() -> None:
    validation = {
        "names": ["hungary"],
        "items": [{"name": "hungary", "exists": True}],
        "error": None,
    }
    result = build_subreddit_list(["hungary"], validation, "en")
    json_str = str(result.to_plotly_json())
    assert "subreddit-status-badge-success" in json_str


def test_build_subreddit_list_with_validation_exists_false_shows_not_found_badge() -> None:
    validation = {
        "names": ["nonexistent"],
        "items": [{"name": "nonexistent", "exists": False}],
        "error": None,
    }
    result = build_subreddit_list(["nonexistent"], validation, "en")
    json_str = str(result.to_plotly_json())
    assert "subreddit-status-badge-error" in json_str


def test_build_subreddit_list_with_no_validation_data_shows_checking_badge() -> None:
    result = build_subreddit_list(["pending_sub"], None, "en")
    json_str = str(result.to_plotly_json())
    assert "subreddit-status-badge-pending" in json_str


def test_build_subreddit_list_with_error_shows_unavailable_header() -> None:
    validation = {
        "names": ["x"],
        "items": [],
        "error": "timeout",
    }
    result = build_subreddit_list(["x"], validation, "en")
    json_str = str(result.to_plotly_json())
    assert "subreddit_validation_unavailable" in json_str or "unavailable" in json_str.lower()


def test_build_subreddit_list_with_names_shows_custom_scope_header() -> None:
    result = build_subreddit_list(["linux"], None, "en")
    json_str = str(result.to_plotly_json())
    assert "custom_subreddit_scope" in json_str or "custom" in json_str.lower()


def test_build_search_history_empty_returns_no_recent_searches() -> None:
    result = build_search_history(None, None, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "no_recent_searches" in json_str or "recent" in json_str.lower()


def test_build_search_history_with_items_renders_buttons() -> None:
    items = [
        {
            "query_run_id": "run-1",
            "term": "linux kernel",
            "status": "completed",
            "saved_at": "2024-01-01T00:00:00Z",
        }
    ]
    result = build_search_history(items, None, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "run-1" in json_str
    assert "linux kernel" in json_str


def test_build_search_history_active_run_has_active_styling() -> None:
    items = [
        {
            "query_run_id": "run-1",
            "term": "test",
            "status": "completed",
            "saved_at": "2024-01-01T00:00:00Z",
        }
    ]
    current_run = {"query_run_id": "run-1"}
    result = build_search_history(items, current_run, "en")
    json_str = str(result.to_plotly_json())
    assert "ring-indigo-100" in json_str


def test_build_search_history_inactive_run_has_default_styling() -> None:
    items = [
        {
            "query_run_id": "run-2",
            "term": "test",
            "status": "completed",
            "saved_at": "2024-01-01T00:00:00Z",
        }
    ]
    current_run = {"query_run_id": "run-1"}
    result = build_search_history(items, current_run, "en")
    json_str = str(result.to_plotly_json())
    assert "ring-indigo-100" not in json_str


def test_build_search_history_skips_items_without_run_id() -> None:
    items: list[dict] = [
        {"term": "no-id-item", "status": "completed"},
        {"query_run_id": "run-1", "term": "valid", "status": "completed", "saved_at": None},
    ]
    result = build_search_history(items, None, "en")
    json_str = str(result.to_plotly_json())
    assert "run-1" in json_str
    assert "no-id-item" not in json_str


def test_build_search_history_caps_at_eight_items() -> None:
    items = [
        {"query_run_id": f"run-{i}", "term": f"term-{i}", "status": "completed", "saved_at": None}
        for i in range(12)
    ]
    result = build_search_history(items, None, "en")
    json_str = str(result.to_plotly_json())
    assert "run-8" not in json_str
    assert "run-7" in json_str
