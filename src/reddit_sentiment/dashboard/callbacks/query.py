from __future__ import annotations

from datetime import UTC, datetime

from dash import ALL, Dash, Input, Output, State, ctx, no_update

from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.core.languages import normalize_content_language
from reddit_sentiment.dashboard.constants import DEFAULT_QUERY_LANGUAGE, settings
from reddit_sentiment.dashboard.helpers import api_request
from reddit_sentiment.dashboard.translations import (
    build_history_status,
    build_status_message,
    normalize_language,
    t,
)


def status_message_class(message: str | None) -> str:
    return "mt-4 text-sm font-medium text-gray-600" if message else "hidden"


def create_query(
    _,
    __,
    language: str | None,
    term: str | None,
    subreddit_names: list[str] | None,
    content_language: str | None,
) -> tuple[dict | None, str, str, bool]:
    if not term:
        message = t(language, "enter_search_term_message")
        return None, message, status_message_class(message), True
    effective_subreddits = subreddit_names or settings.default_subreddits
    effective_content_language = normalize_content_language(content_language)
    payload = {
        "term": term,
        "subreddits": subreddit_names or [],
        "content_language": effective_content_language,
    }
    response = api_request("POST", "/queries", payload)
    if "error" in response:
        message = t(language, "error_prefix", error=response["error"])
        return None, message, status_message_class(message), True
    store_data = {
        **response,
        "term": term,
        "subreddits": effective_subreddits,
        "content_language": effective_content_language,
        "saved_at": datetime.now(UTC).isoformat(),
    }
    is_completed = response.get("status") == QueryRunStatus.completed.value
    message = (
        t(language, "query_completed")
        if is_completed
        else t(language, "query_started", query_run_id=response["query_run_id"])
    )
    return store_data, message, status_message_class(message), is_completed


def poll_query_run(
    _, language: str | None, store_data: dict | None
) -> tuple[dict | None | object, str | object, str | object, bool]:
    if not store_data:
        message = t(language, "no_active_query")
        return None, message, status_message_class(message), True
    run = api_request("GET", f"/query-runs/{store_data['query_run_id']}")
    if "error" in run:
        message = t(language, "error_prefix", error=run["error"])
        return store_data, message, status_message_class(message), True
    if run["status"] == store_data.get("status"):
        return no_update, no_update, no_update, False
    if run["status"] == QueryRunStatus.completed.value:
        message = t(language, "query_completed")
        return (
            {**store_data, "status": run["status"]},
            message,
            status_message_class(message),
            True,
        )
    if run["status"] == QueryRunStatus.failed.value:
        message = t(language, "query_failed", error=run["error_message"])
        return (
            {**store_data, "status": run["status"], "error_message": run.get("error_message")},
            message,
            status_message_class(message),
            True,
        )
    message = t(language, "status_prefix", status=build_history_status(run["status"], language))
    return (
        {**store_data, "status": run["status"]},
        message,
        status_message_class(message),
        False,
    )


def update_history_store(store_data: dict | None, history_items: list[dict] | None) -> list[dict]:
    if not store_data or not store_data.get("query_run_id"):
        return history_items or []

    existing_items = history_items or []
    existing_entry = next(
        (
            item
            for item in existing_items
            if isinstance(item, dict) and item.get("query_run_id") == store_data.get("query_run_id")
        ),
        {},
    )
    updated_entry = {
        **existing_entry,
        "query_run_id": store_data.get("query_run_id"),
        "query_id": store_data.get("query_id"),
        "term": store_data.get("term"),
        "subreddits": store_data.get("subreddits", []),
        "content_language": store_data.get("content_language", DEFAULT_QUERY_LANGUAGE),
        "status": store_data.get("status"),
        "error_message": store_data.get("error_message"),
        "saved_at": existing_entry.get("saved_at")
        or store_data.get("saved_at")
        or datetime.now(UTC).isoformat(),
    }
    merged_items = [updated_entry] + [
        item
        for item in existing_items
        if item.get("query_run_id") != store_data.get("query_run_id")
    ]
    merged_items.sort(key=lambda item: str(item.get("saved_at") or ""), reverse=True)
    return merged_items[:12]


def restore_history_entry(_, language: str | None, history_items: list[dict] | None):
    triggered = ctx.triggered_id
    triggered_value = ctx.triggered[0]["value"] if ctx.triggered else None
    if not isinstance(triggered, dict) or not triggered_value:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    run_id = triggered.get("run_id")
    items = history_items or []
    selected_item = next((item for item in items if item.get("query_run_id") == run_id), None)
    if selected_item is None:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    poll_disabled = selected_item.get("status") in {
        QueryRunStatus.completed.value,
        QueryRunStatus.failed.value,
    }
    message = build_status_message(selected_item, language)
    return (
        selected_item,
        "",
        selected_item.get("subreddits", settings.default_subreddits),
        normalize_language(selected_item.get("content_language")),
        message,
        status_message_class(message),
        poll_disabled,
    )


def register(app: Dash) -> None:
    app.callback(
        Output("query-run-store", "data"),
        Output("status-message", "children"),
        Output("status-message", "className"),
        Output("poll-interval", "disabled"),
        Input("search-button", "n_clicks"),
        Input("term-input", "n_submit"),
        State("language-store", "data"),
        State("term-input", "value"),
        State("subreddit-store", "data"),
        State("content-language-store", "data"),
        prevent_initial_call=True,
    )(create_query)

    app.callback(
        Output("query-run-store", "data", allow_duplicate=True),
        Output("status-message", "children", allow_duplicate=True),
        Output("status-message", "className", allow_duplicate=True),
        Output("poll-interval", "disabled", allow_duplicate=True),
        Input("poll-interval", "n_intervals"),
        State("language-store", "data"),
        State("query-run-store", "data"),
        prevent_initial_call=True,
    )(poll_query_run)

    app.callback(
        Output("history-store", "data"),
        Input("query-run-store", "data"),
        State("history-store", "data"),
        prevent_initial_call=True,
    )(update_history_store)

    app.callback(
        Output("query-run-store", "data", allow_duplicate=True),
        Output("term-input", "value", allow_duplicate=True),
        Output("subreddit-store", "data", allow_duplicate=True),
        Output("content-language-store", "data", allow_duplicate=True),
        Output("status-message", "children", allow_duplicate=True),
        Output("status-message", "className", allow_duplicate=True),
        Output("poll-interval", "disabled", allow_duplicate=True),
        Input({"type": "history-entry", "run_id": ALL}, "n_clicks"),
        State("language-store", "data"),
        State("history-store", "data"),
        prevent_initial_call=True,
    )(restore_history_entry)
