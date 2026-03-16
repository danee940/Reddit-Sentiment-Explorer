from __future__ import annotations

from dash import ALL, Dash, Input, NoUpdate, Output, State, ctx, html, no_update
from dash.development.base_component import Component

from reddit_sentiment.core.languages import normalize_content_language
from reddit_sentiment.dashboard.charts import normalize_tab, normalize_theme
from reddit_sentiment.dashboard.components import (
    binary_toggle,
    build_search_history,
    build_subreddit_list,
    build_tabs,
    content_language_controls,
    subreddit_scope_layout,
)
from reddit_sentiment.dashboard.helpers import api_request, parse_subreddit_input
from reddit_sentiment.dashboard.translations import normalize_language, t


def update_theme_store(
    light_clicks: int | None, dark_clicks: int | None, current_theme: str | None
) -> str:
    triggered = ctx.triggered_id
    if triggered == "theme-toggle-light" and light_clicks:
        return "light"
    if triggered == "theme-toggle-dark" and dark_clicks:
        return "dark"
    return normalize_theme(current_theme)


def update_language_store(
    en_clicks: int | None, hu_clicks: int | None, current_language: str | None
) -> str:
    triggered = ctx.triggered_id
    if triggered == "language-toggle-en" and en_clicks:
        return "en"
    if triggered == "language-toggle-hu" and hu_clicks:
        return "hu"
    return normalize_language(current_language)


def update_content_language_store(selected_language: str | None) -> str:
    return normalize_content_language(selected_language)


def update_active_tab_store(current_tab: str | None) -> str | NoUpdate:
    normalized_tab = normalize_tab(current_tab)
    if current_tab is None or normalized_tab != current_tab:
        return no_update
    return normalized_tab


def render_static_content(language: str | None, theme: str | None, content_language: str | None):
    active_language = normalize_language(language)
    active_theme = normalize_theme(theme)
    active_content_language = normalize_content_language(content_language)
    return (
        t(active_language, "hero_badge"),
        t(active_language, "hero_title"),
        t(active_language, "hero_description"),
        t(active_language, "run_a_search"),
        t(active_language, "enter_search_term"),
        t(active_language, "search"),
        content_language_controls(active_language, active_content_language),
        binary_toggle(
            "theme-toggle",
            active_theme,
            "light",
            t(active_language, "theme_light"),
            "dark",
            t(active_language, "theme_dark"),
        ),
        binary_toggle(
            "language-toggle",
            active_language,
            "en",
            t(active_language, "language_short_en"),
            "hu",
            t(active_language, "language_short_hu"),
        ),
        t(active_language, "tab_subreddit_scope"),
        t(active_language, "tab_search_overview"),
        t(active_language, "tab_sentiment_trends"),
        t(active_language, "tab_subreddit_breakdown"),
        t(active_language, "tab_matched_content"),
        subreddit_scope_layout(active_language),
    )


def update_subreddit_store(
    _,
    __,
    ___,
    language: str | None,
    input_value: str | None,
    subreddit_names: list[str] | None,
    remove_button_ids: list[dict[str, str]] | None,
) -> tuple[object, object, str]:
    current_names = subreddit_names or []
    triggered = ctx.triggered_id
    triggered_value = ctx.triggered[0]["value"] if ctx.triggered else None

    if triggered == "add-subreddit-button":
        parsed_names = parse_subreddit_input(input_value)
        if not parsed_names:
            return no_update, no_update, t(language, "enter_at_least_one_subreddit")

        updated_names = current_names.copy()
        added_names: list[str] = []
        duplicate_names: list[str] = []
        for name in parsed_names:
            if name in updated_names:
                duplicate_names.append(name)
                continue
            updated_names.append(name)
            added_names.append(name)

        if not added_names:
            duplicate_text = ", ".join(f"r/{name}" for name in duplicate_names)
            return no_update, no_update, t(language, "already_added", subreddits=duplicate_text)

        feedback_parts = [
            t(language, "added", subreddits=", ".join(f"r/{name}" for name in added_names))
        ]
        if duplicate_names:
            feedback_parts.append(
                t(
                    language,
                    "skipped_duplicates",
                    subreddits=", ".join(f"r/{name}" for name in duplicate_names),
                )
            )
        return updated_names, "", " ".join(feedback_parts)

    if isinstance(triggered, dict) and triggered.get("type") == "remove-subreddit":
        if not triggered_value:
            return no_update, no_update, ""
        subreddit_name = triggered.get("name")
        valid_remove_names = {item["name"] for item in remove_button_ids or []}
        if subreddit_name not in valid_remove_names:
            return no_update, no_update, ""
        updated_names = [name for name in current_names if name != subreddit_name]
        return updated_names, no_update, t(language, "removed_subreddit", subreddit=subreddit_name)

    return no_update, no_update, ""


def validate_subreddit_list(subreddit_names: list[str] | None) -> dict[str, object]:
    names = subreddit_names or []
    if not names:
        return {"names": [], "items": [], "error": None}
    validation_response = api_request("POST", "/subreddits/validate", {"subreddits": names})
    return {
        "names": names,
        "items": validation_response.get("items", []),
        "error": validation_response.get("error"),
    }


def render_subreddit_list(
    subreddit_names: list[str] | None,
    validation_data: dict | None,
    language: str | None,
) -> html.Div:
    return build_subreddit_list(subreddit_names, validation_data, language)


def render_search_history(
    history_items: list[dict] | None, current_run: dict | None, language: str | None
) -> html.Div:
    return build_search_history(history_items, current_run, language)


def render_tabs(language: str | None, current_tab: str | None) -> Component:
    return build_tabs(language, current_tab)


def register(app: Dash) -> None:
    app.callback(
        Output("theme-store", "data", allow_duplicate=True),
        Input("theme-toggle-light", "n_clicks"),
        Input("theme-toggle-dark", "n_clicks"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )(update_theme_store)

    app.callback(
        Output("language-store", "data", allow_duplicate=True),
        Input("language-toggle-en", "n_clicks"),
        Input("language-toggle-hu", "n_clicks"),
        State("language-store", "data"),
        prevent_initial_call=True,
    )(update_language_store)

    app.callback(
        Output("content-language-store", "data"),
        Input("content-language-dropdown", "value"),
    )(update_content_language_store)

    app.callback(
        Output("active-tab-store", "data"),
        Input("main-tabs", "value"),
    )(update_active_tab_store)

    app.callback(
        Output("hero-badge", "children"),
        Output("hero-title", "children"),
        Output("hero-description", "children"),
        Output("search-panel-title", "children"),
        Output("term-input", "placeholder"),
        Output("search-button", "children"),
        Output("content-language-control", "children"),
        Output("theme-toggle-container", "children"),
        Output("language-toggle-container", "children"),
        Output("main-tab-subreddit-scope", "label"),
        Output("main-tab-search-overview", "label"),
        Output("main-tab-sentiment-trends", "label"),
        Output("main-tab-subreddit-breakdown", "label"),
        Output("main-tab-matched-content", "label"),
        Output("subreddit-scope-container", "children"),
        Input("language-store", "data"),
        Input("theme-store", "data"),
        Input("content-language-store", "data"),
    )(render_static_content)

    app.callback(
        Output("subreddit-store", "data"),
        Output("subreddit-input", "value"),
        Output("subreddit-feedback", "children"),
        Input("add-subreddit-button", "n_clicks"),
        Input("subreddit-input", "n_submit"),
        Input({"type": "remove-subreddit", "name": ALL}, "n_clicks"),
        State("language-store", "data"),
        State("subreddit-input", "value"),
        State("subreddit-store", "data"),
        State({"type": "remove-subreddit", "name": ALL}, "id"),
        prevent_initial_call=True,
    )(update_subreddit_store)

    app.callback(
        Output("subreddit-validation-store", "data"),
        Input("subreddit-store", "data"),
    )(validate_subreddit_list)

    app.callback(
        Output("subreddit-list", "children"),
        Input("subreddit-store", "data"),
        Input("subreddit-validation-store", "data"),
        Input("language-store", "data"),
    )(render_subreddit_list)

    app.callback(
        Output("search-history", "children"),
        Input("history-store", "data"),
        Input("query-run-store", "data"),
        Input("language-store", "data"),
    )(render_search_history)
