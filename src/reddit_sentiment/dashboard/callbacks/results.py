from __future__ import annotations

import plotly.express as px
from dash import Dash, Input, Output, html

from reddit_sentiment.core.enums import QueryRunStatus
from reddit_sentiment.dashboard.charts import (
    build_empty_figure,
    style_distribution_chart,
    style_heatmap_chart,
    style_subreddit_breakdown_chart,
    style_timeline_chart,
)
from reddit_sentiment.dashboard.components import (
    build_document_detail,
    build_documents_layout,
    metric_card,
    section_header,
)
from reddit_sentiment.dashboard.constants import SENTIMENT_COLORS, SENTIMENT_ORDER, settings
from reddit_sentiment.dashboard.helpers import (
    api_request,
    normalize_timeline_items,
    prepare_document_items,
    sort_sentiment_distribution,
)
from reddit_sentiment.dashboard.translations import (
    build_history_status,
    normalize_language,
    t,
    translate_sentiment_label,
)


def _build_distribution_chart(distribution_data: list[dict], active_language: str, active_theme: str):
    if not distribution_data:
        return build_empty_figure(t(active_language, "no_distribution_data"), active_theme)
    return style_distribution_chart(
        px.bar(
            distribution_data,
            x="display_label",
            y="count",
            title=t(active_language, "sentiment_distribution"),
            custom_data=["label"],
            category_orders={
                "display_label": [translate_sentiment_label(label, active_language) for label in SENTIMENT_ORDER]
            },
            color="display_label",
            color_discrete_map={
                translate_sentiment_label(label, active_language): SENTIMENT_COLORS[label] for label in SENTIMENT_ORDER
            },
        ),
        active_theme,
        x_title=t(active_language, "sentiment"),
        y_title=t(active_language, "chart_axis_match_count"),
        hover_label=t(active_language, "chart_hover_match_count"),
    )


def _build_timeline_chart(timeline_data: list[dict], title_key: str, color: str, fill_color: str, active_language: str, active_theme: str, empty_key: str):
    if not timeline_data:
        return build_empty_figure(t(active_language, empty_key), active_theme)
    return style_timeline_chart(
        px.line(timeline_data, x="date", y="average_score", title=t(active_language, title_key), markers=True),
        color=color,
        fill_color=fill_color,
        theme=active_theme,
        x_title=t(active_language, "chart_axis_date"),
        y_title=t(active_language, "chart_axis_average_score"),
        hover_label=t(active_language, "chart_hover_average_score"),
    )


def _build_volume_chart(volume_data: list[dict], active_language: str, active_theme: str):
    if not volume_data:
        return build_empty_figure(t(active_language, "no_volume_data"), active_theme)
    return style_timeline_chart(
        px.line(volume_data, x="date", y="count", title=t(active_language, "volume_over_time"), markers=True),
        color="#0ea5e9",
        fill_color="rgba(14, 165, 233, 0.10)",
        theme=active_theme,
        x_title=t(active_language, "chart_axis_date"),
        y_title=t(active_language, "chart_axis_document_count"),
        hover_label=t(active_language, "chart_hover_document_count"),
    )


def _build_heatmap_chart(heatmap_data: list[dict], active_language: str, active_theme: str):
    if not heatmap_data:
        return build_empty_figure(t(active_language, "no_heatmap_data"), active_theme)
    return style_heatmap_chart(
        px.density_heatmap(
            heatmap_data,
            x="date",
            y="subreddit",
            z="average_score",
            histfunc="avg",
            title=t(active_language, "sentiment_heatmap"),
            color_continuous_scale="RdYlGn",
        ),
        active_theme,
        x_title=t(active_language, "chart_axis_date"),
        y_title=t(active_language, "chart_axis_subreddit"),
        colorbar_title=t(active_language, "chart_axis_average_sentiment"),
    )


def _build_subreddit_chart(subreddit_rows: list[dict], active_language: str, active_theme: str):
    if not subreddit_rows:
        return build_empty_figure(t(active_language, "no_subreddit_data"), active_theme)
    return style_subreddit_breakdown_chart(
        px.bar(
            subreddit_rows,
            x="subreddit",
            y=[
                translate_sentiment_label(label, active_language)
                for label in SENTIMENT_ORDER
                if subreddit_rows and translate_sentiment_label(label, active_language) in subreddit_rows[0]
            ],
            barmode="stack",
            title=t(active_language, "subreddit_breakdown"),
            color_discrete_map={
                translate_sentiment_label(label, active_language): SENTIMENT_COLORS[label] for label in SENTIMENT_ORDER
            },
        ),
        active_theme,
        x_title=t(active_language, "chart_axis_subreddit"),
        y_title=t(active_language, "chart_axis_document_count"),
        hover_label=t(active_language, "chart_hover_document_count"),
    )


def _build_phrase_breakdown(phrase_breakdown: list[dict], active_language: str) -> html.Div:
    if not phrase_breakdown:
        return html.Div(t(active_language, "no_phrase_breakdown"), className="text-sm text-gray-500")
    return html.Div(
        [
            section_header(
                t(active_language, "phrase_breakdown"),
                t(active_language, "phrase_breakdown"),
                t(active_language, "phrase_breakdown_description"),
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                translate_sentiment_label(item.get("label"), active_language),
                                className="text-sm font-semibold text-gray-900",
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        f"{term['term']} ({term['count']})",
                                        className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700",
                                    )
                                    for term in item.get("terms", [])
                                ],
                                className="mt-3 flex flex-wrap gap-2",
                            ),
                        ],
                        className="rounded-2xl border border-gray-200 bg-gray-50 p-4",
                    )
                    for item in phrase_breakdown
                ],
                className="grid gap-4",
            ),
        ]
    )


def _build_spike_events(spike_events: list[dict], active_language: str) -> html.Div:
    if not spike_events:
        return html.Div(t(active_language, "no_spike_events"), className="text-sm text-gray-500")
    return html.Div(
        [
            section_header(
                t(active_language, "spike_analysis"),
                t(active_language, "spike_analysis"),
                t(active_language, "spike_analysis_description"),
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(item.get("date"), className="text-sm font-semibold text-gray-900"),
                            html.Div(
                                f"{t(active_language, 'documents')}: {item.get('count', 0)}",
                                className="mt-2 text-sm text-gray-600",
                            ),
                            html.Div(
                                f"{t(active_language, 'average_score')}: {item.get('average_score', 0.0):.2f}",
                                className="mt-1 text-sm text-gray-600",
                            ),
                            html.Div(
                                f"{t(active_language, 'score_change')}: {item.get('score_change', 0.0):+.2f}",
                                className="mt-1 text-sm text-gray-600",
                            ),
                        ],
                        className="rounded-2xl border border-gray-200 bg-gray-50 p-4",
                    )
                    for item in spike_events
                ],
                className="grid gap-4 lg:grid-cols-2",
            ),
        ]
    )


def _render_completed_results(store_data: dict, active_theme: str, active_language: str) -> tuple:
    charts = api_request("GET", f"/query-runs/{store_data['query_run_id']}/charts")
    documents = api_request("GET", f"/query-runs/{store_data['query_run_id']}/documents")

    overview_data = charts.get("overview", {})
    total_documents = overview_data.get("total_documents", 0)
    average_score = overview_data.get("average_score", 0.0) if overview_data else 0.0
    scope_size = len(store_data.get("subreddits", settings.default_subreddits))
    overview_component = html.Div(
        [
            section_header(
                t(active_language, "overview"),
                t(active_language, "search_overview"),
                t(active_language, "search_overview_description"),
            ),
            html.Div(
                [
                    metric_card(t(active_language, "documents"), str(total_documents)),
                    metric_card(t(active_language, "average_score"), f"{average_score:.2f}"),
                    metric_card(t(active_language, "subreddits"), str(scope_size)),
                    metric_card(
                        t(active_language, "confidence_high"),
                        str(overview_data.get("high_confidence_documents", total_documents)),
                    ),
                    metric_card(t(active_language, "confidence_low"), str(overview_data.get("low_confidence_documents", 0))),
                ],
                className="grid gap-4 md:grid-cols-2 xl:grid-cols-5",
            ),
        ],
        className="space-y-6",
    )

    distribution_data = [
        {**item, "display_label": translate_sentiment_label(str(item.get("label", "")), active_language)}
        for item in sort_sentiment_distribution(charts.get("sentiment_distribution", []))
    ]
    timeline_data = normalize_timeline_items(charts.get("sentiment_timeline", []), "date")
    rolling_data = normalize_timeline_items(charts.get("rolling_sentiment_timeline", []), "date")
    volume_data = normalize_timeline_items(charts.get("volume_timeline", []), "date")
    heatmap_data = charts.get("sentiment_heatmap", [])

    subreddit_rows = []
    for item in charts.get("subreddit_breakdown", []):
        row = {"subreddit": item["subreddit"]}
        for label in SENTIMENT_ORDER:
            row[translate_sentiment_label(label, active_language)] = item["distribution"].get(label, 0)
        subreddit_rows.append(row)

    timeline_chart = _build_timeline_chart(
        timeline_data, "sentiment_over_time", "#4f46e5", "rgba(79, 70, 229, 0.10)", active_language, active_theme, "no_timeline_data"
    )
    rolling_chart = _build_timeline_chart(
        rolling_data, "rolling_sentiment", "#8b5cf6", "rgba(139, 92, 246, 0.10)", active_language, active_theme, "no_rolling_sentiment_data"
    )

    document_items = prepare_document_items(documents.get("items", []), active_language)
    documents_layout = build_documents_layout(
        document_items,
        active_theme,
        active_language,
        build_document_detail(document_items[0] if document_items else None, active_language),
    )

    return (
        overview_component,
        timeline_chart,
        rolling_chart,
        _build_distribution_chart(distribution_data, active_language, active_theme),
        timeline_chart,
        _build_volume_chart(volume_data, active_language, active_theme),
        _build_heatmap_chart(heatmap_data, active_language, active_theme),
        _build_subreddit_chart(subreddit_rows, active_language, active_theme),
        _build_phrase_breakdown(charts.get("phrase_breakdown", []), active_language),
        _build_spike_events(charts.get("spike_events", []), active_language),
        documents_layout,
    )


def render_results(store_data: dict | None, theme: str | None, language: str | None):
    active_theme = theme or "light"
    active_language = normalize_language(language)
    empty_figure = build_empty_figure(t(active_language, "no_data_yet"), active_theme)
    no_phrase = html.Div(t(active_language, "no_phrase_breakdown"), className="text-sm text-gray-500")
    no_spike = html.Div(t(active_language, "no_spike_events"), className="text-sm text-gray-500")

    if not store_data:
        overview = html.Div(
            [
                section_header(
                    t(active_language, "overview"),
                    t(active_language, "overview_empty_title"),
                    t(active_language, "overview_empty_description"),
                ),
                html.Div(
                    [
                        metric_card(t(active_language, "tracked_subreddits"), str(len(settings.default_subreddits))),
                        metric_card(t(active_language, "result_status"), t(active_language, "waiting")),
                        metric_card(t(active_language, "documents"), "0"),
                    ],
                    className="grid gap-4 md:grid-cols-3",
                ),
            ],
            className="space-y-6",
        )
        empty_documents_detail = html.Div(
            [
                html.Div(t(active_language, "matched_content_will_appear"), className="text-lg font-semibold text-gray-900"),
                html.P(t(active_language, "run_search_to_inspect"), className="mt-2 text-sm leading-6 text-gray-600"),
            ],
            className="rounded-3xl border border-dashed border-gray-200 bg-gray-50 p-8",
        )
        return (
            overview,
            empty_figure, empty_figure, empty_figure, empty_figure,
            empty_figure, empty_figure, empty_figure,
            no_phrase, no_spike,
            build_documents_layout([], active_theme, active_language, empty_documents_detail),
        )

    if store_data.get("status") != QueryRunStatus.completed.value:
        pending_figure = build_empty_figure(t(active_language, "results_when_complete"), active_theme)
        pending_overview = html.Div(
            [
                section_header(
                    t(active_language, "overview"),
                    t(active_language, "search_in_progress"),
                    t(active_language, "search_in_progress_description"),
                ),
                html.Div(
                    [
                        metric_card(t(active_language, "query"), store_data.get("term") or t(active_language, "current_run")),
                        metric_card(t(active_language, "status"), build_history_status(store_data.get("status"), active_language)),
                        metric_card(
                            t(active_language, "subreddits"),
                            str(len(store_data.get("subreddits", settings.default_subreddits))),
                        ),
                    ],
                    className="grid gap-4 md:grid-cols-3",
                ),
            ],
            className="space-y-6",
        )
        pending_documents_detail = html.Div(
            [
                html.Div(t(active_language, "search_still_running"), className="text-lg font-semibold text-gray-900"),
                html.P(t(active_language, "search_still_running_description"), className="mt-2 text-sm leading-6 text-gray-600"),
            ],
            className="rounded-3xl border border-dashed border-gray-200 bg-gray-50 p-8",
        )
        return (
            pending_overview,
            pending_figure, pending_figure, pending_figure, pending_figure,
            pending_figure, pending_figure, pending_figure,
            no_phrase, no_spike,
            build_documents_layout([], active_theme, active_language, pending_documents_detail),
        )

    return _render_completed_results(store_data, active_theme, active_language)


def register(app: Dash) -> None:
    app.callback(
        Output("overview-container", "children"),
        Output("overview-timeline-chart", "figure"),
        Output("rolling-sentiment-chart", "figure"),
        Output("sentiment-distribution-chart", "figure"),
        Output("sentiment-timeline-chart", "figure"),
        Output("volume-chart", "figure"),
        Output("sentiment-heatmap-chart", "figure"),
        Output("subreddit-chart", "figure"),
        Output("phrase-breakdown-container", "children"),
        Output("spike-events-container", "children"),
        Output("documents-container", "children"),
        Input("query-run-store", "data"),
        Input("resolved-theme-store", "data"),
        Input("language-store", "data"),
    )(render_results)
