from __future__ import annotations

from typing import Any, cast

from dash import dcc, html
from dash.dash_table._imports_ import DataTable

from reddit_sentiment.dashboard.charts import get_figure_theme
from reddit_sentiment.dashboard.components.base import (
    build_sentiment_badge,
    card_wrapper,
    section_header,
)
from reddit_sentiment.dashboard.constants import SENTIMENT_ORDER
from reddit_sentiment.dashboard.helpers import serialize_document_table_rows
from reddit_sentiment.dashboard.translations import (
    normalize_language,
    t,
    translate_sentiment_label,
    translate_source_label,
)


def build_documents_table(
    document_items: list[dict], theme: str, language: str | None
) -> Any:
    colors = get_figure_theme(theme)
    style_data_conditional = cast(
        Any,
        [
            {
                "if": {"state": "selected"},
                "backgroundColor": colors["table_selected_bg"],
                "border": f"1px solid {colors['table_selected_border']}",
                "color": colors["table_cell_color"],
            }
        ],
    )
    return DataTable(
        id="documents-table",
        data=serialize_document_table_rows(document_items),
        columns=[
            {"name": t(language, "date"), "id": "display_date"},
            {"name": t(language, "subreddit"), "id": "subreddit"},
            {"name": t(language, "sentiment"), "id": "sentiment_text"},
            {"name": t(language, "snippet"), "id": "snippet_preview"},
        ],
        row_selectable="single",
        selected_row_ids=[document_items[0]["id"]] if document_items else [],
        active_cell=(
            {
                "row": 0,
                "column": 0,
                "column_id": "display_date",
                "row_id": document_items[0]["id"],
            }
            if document_items
            else None
        ),
        page_size=8,
        style_as_list_view=True,
        css=[
            {"selector": ".dash-select-header", "rule": "display: none;"},
            {"selector": ".dash-select-cell", "rule": "display: none;"},
        ],
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "whiteSpace": "normal",
            "height": "auto",
            "backgroundColor": colors["table_cell_bg"],
            "color": colors["table_cell_color"],
            "borderBottom": f"1px solid {colors['table_cell_border']}",
            "padding": "14px 16px",
            "fontFamily": "Inter, sans-serif",
            "fontSize": "14px",
            "maxWidth": "0",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_header={
            "backgroundColor": colors["table_header_bg"],
            "color": colors["table_cell_color"],
            "fontWeight": "700",
            "borderBottom": f"1px solid {colors['table_header_border']}",
        },
        style_data={"backgroundColor": colors["table_cell_bg"]},
        style_data_conditional=style_data_conditional,
    )


def build_document_detail(item: dict | None, language: str | None) -> html.Div:
    if item is None:
        return card_wrapper(
            [
                html.Div(
                    t(language, "select_a_match"), className="text-lg font-semibold text-gray-900"
                ),
                html.P(
                    t(language, "select_a_match_description"),
                    className="mt-2 text-sm leading-6 text-gray-600",
                ),
            ],
            "p-6 lg:p-8",
        )

    permalink = item.get("permalink")
    sentiment_confidence = item.get("sentiment_confidence")
    return card_wrapper(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                f"r/{item.get('subreddit', 'unknown')}",
                                className="text-sm font-semibold text-gray-900",
                            ),
                            html.Div(
                                item.get("display_date", t(language, "unknown_date")),
                                className="mt-1 text-sm text-gray-500",
                            ),
                        ]
                    ),
                    build_sentiment_badge(item.get("sentiment_label"), language),
                ],
                className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                t(language, "source"),
                                className="text-xs font-semibold uppercase tracking-wide text-gray-500 break-words whitespace-normal leading-5",
                            ),
                            html.Div(
                                translate_source_label(item.get("source_type"), language),
                                className="mt-1 text-sm font-medium text-gray-900",
                            ),
                        ],
                        className="min-w-0 rounded-2xl bg-gray-50 p-4",
                    ),
                    html.Div(
                        [
                            html.Div(
                                t(language, "score"),
                                className="text-xs font-semibold uppercase tracking-wide text-gray-500 break-words whitespace-normal leading-5",
                            ),
                            html.Div(
                                str(item.get("score") or 0),
                                className="mt-1 text-sm font-medium text-gray-900",
                            ),
                        ],
                        className="min-w-0 rounded-2xl bg-gray-50 p-4",
                    ),
                    html.Div(
                        [
                            html.Div(
                                t(language, "sentiment_confidence"),
                                className="text-xs font-semibold uppercase tracking-wide text-gray-500 break-words whitespace-normal leading-5",
                                lang=normalize_language(language),
                                style={
                                    "hyphens": "auto",
                                    "overflowWrap": "normal",
                                    "wordBreak": "normal",
                                },
                            ),
                            html.Div(
                                (
                                    f"{float(sentiment_confidence):.2f}"
                                    if isinstance(sentiment_confidence, int | float)
                                    else t(language, "unscored")
                                ),
                                className="mt-1 text-sm font-medium text-gray-900",
                            ),
                        ],
                        className="min-w-0 rounded-2xl bg-gray-50 p-4",
                    ),
                ],
                className="mt-6 grid gap-4 sm:grid-cols-3",
            ),
            html.Div(
                [
                    html.Div(
                        t(language, "matched_content"),
                        className="text-xs font-semibold uppercase tracking-wide text-gray-500",
                    ),
                    html.Div(
                        item.get("content")
                        or item.get("snippet")
                        or t(language, "no_content_available"),
                        className="mt-3 min-w-0 whitespace-pre-wrap break-words rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm leading-7 text-gray-700",
                        style={
                            "overflowWrap": "anywhere",
                            "maxHeight": "28rem",
                            "overflowY": "auto",
                        },
                    ),
                ],
                className="mt-6",
            ),
            html.Div(
                [
                    html.Div(
                        t(language, "rationale"),
                        className="text-xs font-semibold uppercase tracking-wide text-gray-500",
                    ),
                    html.Div(
                        item.get("sentiment_rationale") or t(language, "no_phrase_breakdown"),
                        className="mt-3 rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm leading-7 text-gray-700",
                    ),
                ],
                className="mt-6",
            ),
            html.Div(
                [
                    html.Div(
                        t(language, "evidence_phrases"),
                        className="text-xs font-semibold uppercase tracking-wide text-gray-500",
                    ),
                    html.Div(
                        [
                            html.Span(
                                phrase,
                                className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700",
                            )
                            for phrase in item.get("sentiment_evidence_phrases", [])
                        ],
                        className="mt-3 flex flex-wrap gap-2",
                    )
                    if item.get("sentiment_evidence_phrases")
                    else html.Div(
                        t(language, "no_evidence_phrases"),
                        className="mt-3 text-sm text-gray-500",
                    ),
                ],
                className="mt-6",
            ),
            html.Div(
                [
                    html.A(
                        t(language, "open_on_reddit"),
                        href=permalink,
                        target="_blank",
                        rel="noreferrer",
                        className="inline-flex items-center justify-center rounded-xl bg-gray-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-gray-800",
                    )
                    if permalink
                    else html.Span(
                        t(language, "no_permalink_available"), className="text-sm text-gray-500"
                    )
                ],
                className="mt-6",
            ),
        ],
        "p-6 lg:p-8",
    )


def build_documents_layout(
    document_items: list[dict],
    theme: str,
    language: str | None,
    detail_content: html.Div,
) -> html.Div:
    subreddit_options = [
        {"label": f"r/{name}", "value": name}
        for name in sorted({item["subreddit"] for item in document_items})
    ]
    sentiment_options = [
        {"label": translate_sentiment_label(label, language), "value": label}
        for label in SENTIMENT_ORDER
        if any(item.get("sentiment_label") == label for item in document_items)
    ]
    source_options = [
        {"label": translate_source_label(source, language), "value": source}
        for source in sorted({item["source_type"] for item in document_items})
    ]
    documents_table = build_documents_table(document_items, theme, language)
    return html.Div(
        [
            card_wrapper(
                [
                    section_header(
                        t(language, "documents_eyebrow"),
                        t(language, "matched_content_explorer"),
                        t(language, "documents_description"),
                    ),
                    dcc.Store(id="documents-store", data=document_items),
                    html.Div(
                        [
                            dcc.Dropdown(
                                id="document-date-filter",
                                options=[
                                    {"label": value, "value": value}
                                    for value in sorted(
                                        {
                                            item["date_bucket"]
                                            for item in document_items
                                            if item.get("date_bucket")
                                        }
                                    )
                                ],
                                placeholder=t(language, "filter_by_date"),
                                clearable=True,
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Dropdown(
                                id="document-subreddit-filter",
                                options=subreddit_options,
                                placeholder=t(language, "filter_by_subreddit"),
                                clearable=True,
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Dropdown(
                                id="document-sentiment-filter",
                                options=sentiment_options,
                                placeholder=t(language, "filter_by_sentiment"),
                                clearable=True,
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Dropdown(
                                id="document-source-filter",
                                options=source_options,
                                placeholder=t(language, "filter_by_source"),
                                clearable=True,
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="document-search-input",
                                type="text",
                                placeholder=t(language, "search_snippet_text"),
                                debounce=True,
                                className="w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100",
                                style={
                                    "height": "52px",
                                    "lineHeight": "24px",
                                    "padding": "12px 16px",
                                },
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Button(
                                t(language, "clear_filters"),
                                id="clear-chart-filters-button",
                                n_clicks=0,
                                type="button",
                                className="inline-flex items-center justify-center rounded-xl border border-gray-200 px-4 py-3 text-sm font-medium text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50",
                            ),
                        ],
                        className="grid gap-4 md:grid-cols-2 xl:grid-cols-3",
                    ),
                    html.Div(
                        id="documents-summary", className="mt-4 text-sm font-medium text-gray-500"
                    ),
                    html.Div(
                        [
                            html.Div(documents_table, className="xl:col-span-7"),
                            html.Div(
                                id="document-detail",
                                children=detail_content,
                                className="xl:col-span-5 lg:sticky lg:top-6 self-start",
                            ),
                        ],
                        className="mt-6 grid gap-6 xl:grid-cols-12",
                    ),
                ],
                "p-6 lg:p-8",
            )
        ]
    )
