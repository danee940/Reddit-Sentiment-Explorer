from __future__ import annotations

from dash import dcc, html

from reddit_sentiment.dashboard.charts import normalize_tab, normalize_theme
from reddit_sentiment.dashboard.components.base import (
    binary_toggle,
    card_wrapper,
    chart_card,
    section_header,
)
from reddit_sentiment.dashboard.constants import (
    CONTENT_LANGUAGE_OPTIONS,
    DEFAULT_QUERY_LANGUAGE,
    HERO_CHART_HEIGHT_CLASS,
    INPUT_STYLE,
    settings,
)
from reddit_sentiment.dashboard.helpers import get_default_subreddit_text
from reddit_sentiment.dashboard.translations import (
    build_history_status,
    format_history_time,
    format_selected_subreddit_count,
    normalize_language,
    t,
)


def theme_controls(language: str | None, theme: str | None) -> html.Div:
    return html.Div(
        [
            html.Div(
                binary_toggle(
                    "theme-toggle",
                    normalize_theme(theme),
                    "light",
                    t(language, "theme_light"),
                    "dark",
                    t(language, "theme_dark"),
                ),
                id="theme-toggle-container",
            ),
        ],
        className="lg:max-w-[9rem]",
    )


def language_controls(language: str | None) -> html.Div:
    active_language = normalize_language(language)
    return html.Div(
        [
            html.Div(
                binary_toggle(
                    "language-toggle",
                    active_language,
                    "en",
                    t(active_language, "language_short_en"),
                    "hu",
                    t(active_language, "language_short_hu"),
                ),
                id="language-toggle-container",
            ),
        ],
        className="lg:max-w-[9rem]",
    )


def content_language_controls(language: str | None, content_language: str | None) -> html.Div:
    active_language = normalize_language(language)
    selected_language = content_language or DEFAULT_QUERY_LANGUAGE
    return html.Div(
        [
            html.Div(
                t(active_language, "content_language"),
                className="text-xs font-semibold uppercase tracking-widest text-indigo-100",
            ),
            dcc.Dropdown(
                id="content-language-dropdown",
                options=CONTENT_LANGUAGE_OPTIONS,
                value=selected_language,
                clearable=False,
                searchable=False,
                className="mt-3 dash-dropdown hero-language-dropdown",
            ),
        ],
        className="rounded-2xl bg-white bg-opacity-10 p-3 backdrop-blur-sm",
    )


def build_hero_section(language: str | None, theme: str | None) -> html.Div:
    active_language = normalize_language(language)
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                t(active_language, "hero_badge"),
                                id="hero-badge",
                                className="inline-flex rounded-full bg-white bg-opacity-10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-indigo-100",
                            ),
                            html.H1(
                                t(active_language, "hero_title"),
                                id="hero-title",
                                className="mt-5 text-4xl font-bold tracking-tight text-white sm:text-5xl",
                            ),
                            html.P(
                                t(active_language, "hero_description"),
                                id="hero-description",
                                className="mt-4 max-w-2xl text-base leading-7 text-indigo-100",
                            ),
                        ],
                        className="max-w-3xl",
                    ),
                    html.Div(
                        [
                            language_controls(active_language),
                            theme_controls(active_language, theme),
                            html.Div(
                                id="content-language-control",
                                children=content_language_controls(
                                    active_language, DEFAULT_QUERY_LANGUAGE
                                ),
                            ),
                        ],
                        className="flex flex-col gap-3 lg:w-[16rem] lg:shrink-0 lg:items-end",
                    ),
                ],
                className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between",
            ),
            card_wrapper(
                [
                    html.Div(
                        t(active_language, "run_a_search"),
                        id="search-panel-title",
                        className="text-sm font-semibold text-gray-900",
                    ),
                    html.Div(
                        [
                            dcc.Input(
                                id="term-input",
                                type="text",
                                placeholder=t(active_language, "enter_search_term"),
                                debounce=True,
                                className="dashboard-text-input w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100",
                                style=INPUT_STYLE,
                            ),
                            html.Button(
                                t(active_language, "search"),
                                id="search-button",
                                n_clicks=0,
                                className="dashboard-action-button inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500",
                            ),
                        ],
                        className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center",
                    ),
                    html.Div(
                        id="status-message",
                        className="hidden",
                        role="status",
                    ),
                    html.Div(id="search-history", className="mt-4"),
                ],
                "p-5",
            ),
        ],
        className="rounded-3xl bg-gradient-to-br from-gray-900 via-indigo-800 to-blue-700 px-6 py-8 shadow-2xl sm:px-8 lg:px-10",
    )


def subreddit_scope_layout(language: str | None) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    card_wrapper(
                        [
                            section_header(
                                t(language, "configuration"),
                                t(language, "subreddit_scope_title"),
                                t(language, "subreddit_scope_description"),
                            ),
                            html.Div(
                                [
                                    dcc.Input(
                                        id="subreddit-input",
                                        type="text",
                                        placeholder=t(language, "add_subreddit_names"),
                                        debounce=True,
                                        className="dashboard-text-input w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100",
                                        style=INPUT_STYLE,
                                    ),
                                    html.Button(
                                        t(language, "add_subreddits"),
                                        id="add-subreddit-button",
                                        n_clicks=0,
                                        className="dashboard-action-button inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500",
                                    ),
                                ],
                                className="flex flex-col gap-3 sm:flex-row",
                            ),
                            html.Div(
                                t(
                                    language,
                                    "subreddit_help_text",
                                    defaults=get_default_subreddit_text(),
                                ),
                                id="subreddit-help-text",
                                className="mt-4 text-sm leading-6 text-gray-500",
                            ),
                            html.Div(
                                id="subreddit-feedback",
                                className="mt-4 text-sm font-medium text-gray-700",
                            ),
                        ],
                        "p-6 lg:p-8",
                    ),
                    card_wrapper(
                        [
                            html.Div(
                                t(language, "search_scope"),
                                className="text-sm font-semibold text-gray-900",
                            ),
                            html.P(
                                t(language, "search_scope_description"),
                                className="mt-2 text-sm leading-6 text-gray-600",
                            ),
                            html.Div(id="subreddit-list", className="mt-6"),
                        ],
                        "p-6 lg:p-8",
                    ),
                ],
                className="grid gap-6 xl:grid-cols-2",
            )
        ],
        className="space-y-6",
    )


def build_tabs(language: str | None, current_tab: str | None) -> dcc.Tabs:
    active_language = normalize_language(language)
    active_tab = normalize_tab(current_tab)
    return dcc.Tabs(
        id="main-tabs",
        value=active_tab,
        children=[
            dcc.Tab(
                id="main-tab-subreddit-scope",
                label=t(active_language, "tab_subreddit_scope"),
                value="subreddit-scope",
                children=[
                    html.Div(
                        id="subreddit-scope-container",
                        children=subreddit_scope_layout(active_language),
                        className="pt-6",
                    )
                ],
                className="theme-tab",
                selected_className="theme-tab-selected",
            ),
            dcc.Tab(
                id="main-tab-search-overview",
                label=t(active_language, "tab_search_overview"),
                value="search-overview",
                children=[
                    html.Div(
                        [
                            card_wrapper(html.Div(id="overview-container"), "p-6 lg:p-8"),
                            chart_card("overview-timeline-chart", HERO_CHART_HEIGHT_CLASS),
                            chart_card("rolling-sentiment-chart"),
                            chart_card("sentiment-distribution-chart"),
                        ],
                        className="space-y-6 pt-6",
                    )
                ],
                className="theme-tab",
                selected_className="theme-tab-selected",
            ),
            dcc.Tab(
                id="main-tab-sentiment-trends",
                label=t(active_language, "tab_sentiment_trends"),
                value="sentiment-trends",
                children=[
                    html.Div(
                        [
                            chart_card("sentiment-timeline-chart", HERO_CHART_HEIGHT_CLASS),
                            chart_card("volume-chart"),
                            chart_card("sentiment-heatmap-chart"),
                        ],
                        className="grid gap-6 pt-6",
                    )
                ],
                className="theme-tab",
                selected_className="theme-tab-selected",
            ),
            dcc.Tab(
                id="main-tab-subreddit-breakdown",
                label=t(active_language, "tab_subreddit_breakdown"),
                value="subreddit-breakdown",
                children=[
                    html.Div(
                        [
                            chart_card("subreddit-chart"),
                            card_wrapper(html.Div(id="phrase-breakdown-container"), "p-6 lg:p-8"),
                            card_wrapper(html.Div(id="spike-events-container"), "p-6 lg:p-8"),
                        ],
                        className="space-y-6 pt-6",
                    )
                ],
                className="theme-tab",
                selected_className="theme-tab-selected",
            ),
            dcc.Tab(
                id="main-tab-matched-content",
                label=t(active_language, "tab_matched_content"),
                value="matched-content",
                children=[html.Div(id="documents-container", className="pt-6")],
                className="theme-tab",
                selected_className="theme-tab-selected",
            ),
        ],
        colors={"border": "transparent", "primary": "transparent", "background": "transparent"},
        style={"fontFamily": "Inter, sans-serif"},
    )


def build_app_layout() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div(id="hero-container", children=build_hero_section("en", "light")),
                    dcc.Store(id="resolved-theme-store", data="light", storage_type="memory"),
                    dcc.Store(id="theme-store", data=None, storage_type="local"),
                    dcc.Store(id="language-store", data="en", storage_type="local"),
                    dcc.Store(
                        id="content-language-store",
                        data=DEFAULT_QUERY_LANGUAGE,
                        storage_type="session",
                    ),
                    dcc.Store(
                        id="active-tab-store", data="subreddit-scope", storage_type="session"
                    ),
                    dcc.Interval(
                        id="theme-sync-interval", interval=250, n_intervals=0, max_intervals=1
                    ),
                    dcc.Interval(
                        id="language-sync-interval", interval=250, n_intervals=0, max_intervals=1
                    ),
                    dcc.Store(
                        id="subreddit-store",
                        data=settings.default_subreddits,
                        storage_type="session",
                    ),
                    dcc.Store(id="query-run-store", storage_type="session"),
                    dcc.Store(id="history-store", data=[], storage_type="local"),
                    dcc.Store(
                        id="subreddit-validation-store",
                        data={"names": [], "items": [], "error": None},
                    ),
                    dcc.Interval(id="poll-interval", interval=5_000, n_intervals=0, disabled=True),
                    card_wrapper(
                        html.Div(id="tabs-container", children=build_tabs("en", "subreddit-scope")),
                        "mt-8 p-3 sm:p-4",
                    ),
                ],
                className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8",
            )
        ],
        id="app-shell",
        className="theme-shell theme-light min-h-screen",
        style={"fontFamily": "Inter, sans-serif"},
    )


def build_subreddit_list(
    subreddit_names: list[str] | None,
    validation_data: dict | None,
    language: str | None,
) -> html.Div:
    names = subreddit_names or []
    if not names:
        return html.Div(
            [
                html.Div(
                    t(language, "using_env_defaults"),
                    className="text-sm font-semibold text-gray-900",
                ),
                html.Div(
                    get_default_subreddit_text(), className="mt-2 text-sm leading-6 text-gray-600"
                ),
            ],
            className="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-4",
        )

    stored_names = (validation_data or {}).get("names", [])
    validation_items = (validation_data or {}).get("items", []) if stored_names == names else []
    validation_map = {item["name"]: item["exists"] for item in validation_items if "name" in item}

    if (validation_data or {}).get("error"):
        header = html.Div(
            t(language, "subreddit_validation_unavailable"),
            className="text-sm font-semibold text-gray-900",
        )
    else:
        header = html.Div(
            t(language, "custom_subreddit_scope"), className="text-sm font-semibold text-gray-900"
        )

    items = []
    for name in names:
        exists = validation_map.get(name)
        if exists is True:
            status = html.Span(
                t(language, "exists"),
                className="subreddit-status-badge subreddit-status-badge-success",
            )
        elif exists is False:
            status = html.Span(
                t(language, "not_found"),
                className="subreddit-status-badge subreddit-status-badge-error",
            )
        else:
            status = html.Span(
                t(language, "checking"),
                className="subreddit-status-badge subreddit-status-badge-pending",
            )

        items.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                f"r/{name}", className="text-base font-semibold text-gray-900"
                            ),
                            status,
                        ],
                        className="flex flex-wrap items-center gap-3",
                    ),
                    html.Button(
                        t(language, "remove"),
                        id={"type": "remove-subreddit", "name": name},
                        n_clicks=0,
                        className="inline-flex items-center rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50",
                    ),
                ],
                className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-4 shadow-sm sm:flex-row sm:items-center sm:justify-between",
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    header,
                    html.Div(
                        format_selected_subreddit_count(language, len(names)),
                        className="text-sm text-gray-500",
                    ),
                ],
                className="mb-4 flex flex-col gap-2 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 sm:flex-row sm:items-center sm:justify-between",
            ),
            html.Div(items, className="space-y-3"),
        ]
    )


def build_search_history(
    history_items: list[dict] | None,
    current_run: dict | None,
    language: str | None,
) -> html.Div:
    items = history_items or []
    active_run_id = (current_run or {}).get("query_run_id")
    if not items:
        return html.Div(t(language, "no_recent_searches"), className="text-sm text-gray-500")

    buttons = []
    for item in items[:8]:
        run_id = item.get("query_run_id")
        if not run_id:
            continue
        is_active = run_id == active_run_id
        button_class = "rounded-2xl border px-4 py-3 text-left transition " + (
            "border-indigo-200 bg-indigo-50 shadow-sm ring-1 ring-indigo-100"
            if is_active
            else "border-gray-200 bg-gray-50 hover:border-indigo-200 hover:bg-white"
        )
        buttons.append(
            html.Button(
                [
                    html.Div(
                        item.get("term") or t(language, "untitled_search"),
                        className="text-left text-sm font-semibold text-gray-900",
                    ),
                    html.Div(
                        f"{build_history_status(item.get('status'), language)} · {format_history_time(item.get('saved_at'), language)}",
                        className="mt-1 text-left text-xs text-gray-500",
                    ),
                ],
                id={"type": "history-entry", "run_id": run_id},
                n_clicks=0,
                className=button_class,
            )
        )

    return html.Div(
        [
            html.Div(
                t(language, "recent_searches"),
                className="mb-2 text-xs font-semibold uppercase tracking-widest text-gray-400",
            ),
            html.Div(buttons, className="grid gap-3 sm:grid-cols-2"),
        ]
    )
