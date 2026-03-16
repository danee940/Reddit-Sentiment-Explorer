from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, html, no_update

from reddit_sentiment.dashboard.components import build_document_detail
from reddit_sentiment.dashboard.helpers import serialize_document_table_rows
from reddit_sentiment.dashboard.translations import format_matches_summary


def filter_document_rows(
    items: list[dict] | None,
    date_bucket: str | None,
    subreddit: str | None,
    sentiment: str | None,
    source_type: str | None,
    search_text: str | None,
    language: str | None,
) -> tuple[list[dict], list[str], str]:
    document_items = items or []
    normalized_search = (search_text or "").strip().lower()
    filtered_items = []
    for item in document_items:
        if subreddit and item.get("subreddit") != subreddit:
            continue
        if sentiment and item.get("sentiment_label") != sentiment:
            continue
        if source_type and item.get("source_type") != source_type:
            continue
        if date_bucket and item.get("date_bucket") != date_bucket:
            continue
        haystack = " ".join([
            str(item.get("snippet_preview") or ""),
            str(item.get("content") or ""),
            str(item.get("subreddit") or ""),
        ]).lower()
        if normalized_search and normalized_search not in haystack:
            continue
        filtered_items.append(item)

    subreddit_count = len({item.get("subreddit") for item in filtered_items})
    summary = format_matches_summary(language, len(filtered_items), subreddit_count)
    return (
        serialize_document_table_rows(filtered_items),
        [filtered_items[0]["id"]] if filtered_items else [],
        summary,
    )


def render_document_detail(
    document_items: list[dict] | None,
    selected_row_ids: list[str] | None,
    active_cell: dict | None,
    language: str | None,
) -> html.Div:
    rows = document_items or []
    if not rows:
        return build_document_detail(None, language)
    selected_id = None
    if active_cell and active_cell.get("row_id") is not None:
        selected_id = str(active_cell["row_id"])
    elif selected_row_ids:
        selected_id = str(selected_row_ids[0])
    for row in rows:
        if str(row.get("id")) == selected_id:
            return build_document_detail(row, language)
    return build_document_detail(rows[0], language)


def sync_selected_row_from_active_cell(
    active_cell: dict | None,
    viewport_rows: list[dict] | None,
) -> list[str]:
    if not active_cell or active_cell.get("row") is None:
        return []
    rows = viewport_rows or []
    row_index = int(active_cell["row"])
    if row_index >= len(rows):
        return []
    row_id = rows[row_index].get("id")
    if row_id is not None:
        return [str(row_id)]
    return []


def sync_filters_from_chart_clicks(
    sentiment_timeline_click: dict | None,
    volume_timeline_click: dict | None,
    subreddit_chart_click: dict | None,
    sentiment_distribution_click: dict | None,
    clear_clicks: int | None,
):
    triggered = ctx.triggered_id
    if triggered == "clear-chart-filters-button" and clear_clicks:
        return None, None, None, None, ""
    if triggered in {"sentiment-timeline-chart", "volume-chart"}:
        click_data = sentiment_timeline_click if triggered == "sentiment-timeline-chart" else volume_timeline_click
        points = (click_data or {}).get("points") or []
        if not points:
            return no_update, no_update, no_update, no_update, no_update
        date_bucket = points[0].get("x")
        if date_bucket:
            return str(date_bucket), no_update, no_update, no_update, no_update
        return no_update, no_update, no_update, no_update, no_update
    if triggered == "subreddit-chart":
        points = (subreddit_chart_click or {}).get("points") or []
        if not points:
            return no_update, no_update, no_update, no_update, no_update
        subreddit_name = points[0].get("x")
        if subreddit_name:
            return no_update, str(subreddit_name), no_update, no_update, no_update
        return no_update, no_update, no_update, no_update, no_update
    if triggered == "sentiment-distribution-chart":
        points = (sentiment_distribution_click or {}).get("points") or []
        if not points:
            return no_update, no_update, no_update, no_update, no_update
        custom_data = points[0].get("customdata") or []
        sentiment_label = custom_data[0] if custom_data else None
        if sentiment_label:
            return no_update, no_update, str(sentiment_label), no_update, no_update
        return no_update, no_update, no_update, no_update, no_update
    return no_update, no_update, no_update, no_update, no_update


def toggle_clear_filters_button(
    date_bucket: str | None,
    subreddit: str | None,
    sentiment: str | None,
    source_type: str | None,
    search_text: str | None,
) -> bool:
    return not any([date_bucket, subreddit, sentiment, source_type, (search_text or "").strip()])


def register(app: Dash) -> None:
    app.callback(
        Output("document-date-filter", "value", allow_duplicate=True),
        Output("document-subreddit-filter", "value", allow_duplicate=True),
        Output("document-sentiment-filter", "value", allow_duplicate=True),
        Output("document-source-filter", "value", allow_duplicate=True),
        Output("document-search-input", "value", allow_duplicate=True),
        Input("sentiment-timeline-chart", "clickData", allow_optional=True),
        Input("volume-chart", "clickData", allow_optional=True),
        Input("subreddit-chart", "clickData", allow_optional=True),
        Input("sentiment-distribution-chart", "clickData", allow_optional=True),
        Input("clear-chart-filters-button", "n_clicks", allow_optional=True),
        prevent_initial_call=True,
    )(sync_filters_from_chart_clicks)

    app.callback(
        Output("clear-chart-filters-button", "disabled"),
        Input("document-date-filter", "value", allow_optional=True),
        Input("document-subreddit-filter", "value", allow_optional=True),
        Input("document-sentiment-filter", "value", allow_optional=True),
        Input("document-source-filter", "value", allow_optional=True),
        Input("document-search-input", "value", allow_optional=True),
    )(toggle_clear_filters_button)

    app.callback(
        Output("documents-table", "data"),
        Output("documents-table", "selected_row_ids"),
        Output("documents-summary", "children"),
        Input("documents-store", "data", allow_optional=True),
        Input("document-date-filter", "value", allow_optional=True),
        Input("document-subreddit-filter", "value", allow_optional=True),
        Input("document-sentiment-filter", "value", allow_optional=True),
        Input("document-source-filter", "value", allow_optional=True),
        Input("document-search-input", "value", allow_optional=True),
        Input("language-store", "data"),
    )(filter_document_rows)

    app.callback(
        Output("document-detail", "children"),
        Input("documents-store", "data", allow_optional=True),
        Input("documents-table", "selected_row_ids", allow_optional=True),
        Input("documents-table", "active_cell", allow_optional=True),
        Input("language-store", "data"),
    )(render_document_detail)

    app.callback(
        Output("documents-table", "selected_row_ids", allow_duplicate=True),
        Input("documents-table", "active_cell", allow_optional=True),
        State("documents-table", "derived_viewport_data", allow_optional=True),
        prevent_initial_call=True,
    )(sync_selected_row_from_active_cell)
