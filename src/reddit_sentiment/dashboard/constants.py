from __future__ import annotations

from dash.dcc.Graph import Graph

from reddit_sentiment.core.config import get_settings
from reddit_sentiment.core.languages import (
    DEFAULT_CONTENT_LANGUAGE,
    SUPPORTED_UI_LANGUAGES,
    get_content_language_options,
)

settings = get_settings()

TAILWIND_URL = "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css"
FONT_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
GRAPH_CONFIG: Graph.Config = {"displayModeBar": False, "responsive": True}
CHART_HEIGHT_CLASS = "h-[34rem]"
HERO_CHART_HEIGHT_CLASS = "h-[40rem]"
INPUT_STYLE = {
    "height": "52px",
    "lineHeight": "24px",
    "padding": "12px 16px",
}
SENTIMENT_COLORS = {
    "very_negative": "#7f1d1d",
    "negative": "#ef4444",
    "neutral": "#94a3b8",
    "positive": "#22c55e",
    "very_positive": "#15803d",
}
SENTIMENT_ORDER = [
    "very_negative",
    "negative",
    "neutral",
    "positive",
    "very_positive",
]
FIGURE_THEME = {
    "light": {
        "paper_bgcolor": "rgba(255,255,255,0)",
        "plot_bgcolor": "rgba(255,255,255,1)",
        "font_color": "#111827",
        "title_color": "#111827",
        "legend_color": "#4b5563",
        "hover_bgcolor": "#111827",
        "hover_bordercolor": "#111827",
        "hover_font_color": "#f9fafb",
        "grid_color": "rgba(243,244,246,1)",
        "line_color": "rgba(209,213,219,1)",
        "tick_color": "#6b7280",
        "marker_line_color": "#ffffff",
        "table_cell_bg": "#ffffff",
        "table_cell_color": "#111827",
        "table_cell_border": "#f1f5f9",
        "table_header_bg": "#f9fafb",
        "table_header_border": "#e5e7eb",
        "table_selected_bg": "#eef2ff",
        "table_selected_border": "#c7d2fe",
    },
    "dark": {
        "paper_bgcolor": "rgba(15,23,42,0)",
        "plot_bgcolor": "rgba(15,23,42,1)",
        "font_color": "#e5e7eb",
        "title_color": "#f8fafc",
        "legend_color": "#cbd5e1",
        "hover_bgcolor": "#020617",
        "hover_bordercolor": "#020617",
        "hover_font_color": "#f8fafc",
        "grid_color": "rgba(51,65,85,1)",
        "line_color": "rgba(71,85,105,1)",
        "tick_color": "#cbd5e1",
        "marker_line_color": "#0f172a",
        "table_cell_bg": "#0f172a",
        "table_cell_color": "#e5e7eb",
        "table_cell_border": "#1e293b",
        "table_header_bg": "#111827",
        "table_header_border": "#334155",
        "table_selected_bg": "#1e293b",
        "table_selected_border": "#475569",
    },
}
SUPPORTED_LANGUAGES = SUPPORTED_UI_LANGUAGES
DEFAULT_QUERY_LANGUAGE = DEFAULT_CONTENT_LANGUAGE
CONTENT_LANGUAGE_OPTIONS = get_content_language_options()
