from __future__ import annotations

from typing import Any, cast

from dash import dcc, html

from reddit_sentiment.dashboard.constants import CHART_HEIGHT_CLASS, GRAPH_CONFIG
from reddit_sentiment.dashboard.translations import translate_sentiment_label


def metric_card(label: str, value: str) -> html.Div:
    return html.Div(
        [
            html.Div(label, className="text-xs font-semibold uppercase tracking-wide text-gray-500"),
            html.Div(value, className="mt-3 text-3xl font-bold tracking-tight text-gray-900"),
        ],
        className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm",
    )


def section_header(eyebrow: str, title: str, description: str) -> html.Div:
    return html.Div(
        [
            html.Div(eyebrow, className="text-xs font-semibold uppercase tracking-widest text-indigo-600"),
            html.H2(title, className="mt-3 text-2xl font-bold tracking-tight text-gray-900"),
            html.P(description, className="mt-2 max-w-3xl text-sm leading-6 text-gray-600"),
        ],
        className="mb-6",
    )


def card_wrapper(children, class_name: str = "") -> html.Div:
    base_class = "rounded-3xl border border-gray-200 bg-white shadow-sm"
    return html.Div(children, className=f"{base_class} {class_name}".strip())


def binary_toggle(
    toggle_name: str,
    active_value: str,
    left_value: str,
    left_label: str,
    right_value: str,
    right_label: str,
) -> html.Div:
    active_class = "binary-toggle-right" if active_value == right_value else "binary-toggle-left"
    return html.Div(
        [
            html.Div(className="binary-toggle-knob"),
            html.Button(
                left_label,
                id=f"{toggle_name}-{left_value}",
                n_clicks=0,
                type="button",
                **cast(
                    Any,
                    {"aria-pressed": "true" if active_value == left_value else "false"},
                ),
                className=(
                    "binary-toggle-button "
                    + (
                        "binary-toggle-button-active"
                        if active_value == left_value
                        else "binary-toggle-button-inactive"
                    )
                ),
            ),
            html.Button(
                right_label,
                id=f"{toggle_name}-{right_value}",
                n_clicks=0,
                type="button",
                **cast(
                    Any,
                    {"aria-pressed": "true" if active_value == right_value else "false"},
                ),
                className=(
                    "binary-toggle-button "
                    + (
                        "binary-toggle-button-active"
                        if active_value == right_value
                        else "binary-toggle-button-inactive"
                    )
                ),
            ),
        ],
        className=f"binary-toggle {active_class}",
    )


_SENTIMENT_BADGE_VARIANTS: dict[str, str] = {
    "very_negative": "sentiment-badge--very-negative",
    "negative": "sentiment-badge--negative",
    "neutral": "sentiment-badge--neutral",
    "positive": "sentiment-badge--positive",
    "very_positive": "sentiment-badge--very-positive",
    "unscored": "sentiment-badge--unscored",
}


def build_sentiment_badge(label: str | None, language: str | None) -> html.Span:
    stripped = (label or "").strip()
    normalized = stripped.lower() if stripped else "unscored"
    if normalized in _SENTIMENT_BADGE_VARIANTS:
        variant_class = _SENTIMENT_BADGE_VARIANTS[normalized]
        text_key = normalized
    else:
        variant_class = _SENTIMENT_BADGE_VARIANTS["unscored"]
        text_key = stripped or "unscored"
    return html.Span(
        translate_sentiment_label(text_key, language),
        className=f"sentiment-badge {variant_class}",
    )


def chart_card(graph_id: str, height_class: str = CHART_HEIGHT_CLASS) -> html.Div:
    return card_wrapper(
        dcc.Graph(id=graph_id, config=GRAPH_CONFIG, className=height_class),
        "overflow-hidden p-2",
    )
