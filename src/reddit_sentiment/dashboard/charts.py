from __future__ import annotations

import plotly.express as px

from reddit_sentiment.dashboard.constants import FIGURE_THEME


def normalize_theme(value: str | None) -> str:
    return value if value in {"light", "dark"} else "light"


def normalize_tab(value: str | None) -> str:
    valid_tabs = {
        "subreddit-scope",
        "search-overview",
        "sentiment-trends",
        "subreddit-breakdown",
        "matched-content",
    }
    return value if value in valid_tabs else "subreddit-scope"


def get_figure_theme(theme: str | None) -> dict[str, str]:
    normalized_theme = (theme or "light").lower()
    if normalized_theme not in FIGURE_THEME:
        normalized_theme = "light"
    return FIGURE_THEME[normalized_theme]


def build_empty_figure(title: str, theme: str = "light"):
    figure = px.line(title=title)
    return style_figure(figure, theme)


def style_figure(figure, theme: str = "light"):
    colors = get_figure_theme(theme)
    figure.update_layout(
        template="simple_white",
        paper_bgcolor=colors["paper_bgcolor"],
        plot_bgcolor=colors["plot_bgcolor"],
        font={"color": colors["font_color"], "family": "Inter, sans-serif"},
        colorway=["#4f46e5", "#06b6d4", "#0ea5e9", "#8b5cf6", "#10b981"],
        title={"font": {"size": 18, "color": colors["title_color"]}},
        margin={"l": 20, "r": 20, "t": 56, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.04,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 12, "color": colors["legend_color"]},
        },
        hoverlabel={
            "bgcolor": colors["hover_bgcolor"],
            "bordercolor": colors["hover_bordercolor"],
            "font": {"color": colors["hover_font_color"], "family": "Inter, sans-serif"},
        },
    )
    figure.update_xaxes(
        gridcolor=colors["grid_color"],
        zerolinecolor=colors["grid_color"],
        linecolor=colors["line_color"],
        tickfont={"size": 13, "color": colors["tick_color"]},
        title_font={"size": 13, "color": colors["tick_color"]},
    )
    figure.update_yaxes(
        gridcolor=colors["grid_color"],
        zerolinecolor=colors["grid_color"],
        linecolor=colors["line_color"],
        tickfont={"size": 13, "color": colors["tick_color"]},
        title_font={"size": 13, "color": colors["tick_color"]},
    )
    return figure


def style_distribution_chart(
    figure,
    theme: str = "light",
    x_title: str | None = None,
    y_title: str | None = None,
    hover_label: str | None = None,
):
    figure = style_figure(figure, theme)
    figure.update_traces(
        marker_line_width=0,
        hovertemplate=f"%{{x}}<br>{hover_label}: %{{y}}<extra></extra>" if hover_label else "%{x}: %{y}<extra></extra>",
    )
    figure.update_layout(showlegend=False)
    if x_title:
        figure.update_xaxes(title_text=x_title)
    if y_title:
        figure.update_yaxes(title_text=y_title)
    return figure


def style_timeline_chart(
    figure,
    color: str,
    fill_color: str,
    theme: str = "light",
    x_title: str | None = None,
    y_title: str | None = None,
    hover_label: str | None = None,
):
    colors = get_figure_theme(theme)
    figure = style_figure(figure, theme)
    figure.update_traces(
        mode="lines+markers",
        line={"width": 4, "shape": "spline", "color": color},
        marker={"size": 8, "color": color, "line": {"width": 2, "color": colors["marker_line_color"]}},
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate=f"%{{x}}<br>{hover_label}: %{{y}}<extra></extra>" if hover_label else "%{x}<br>%{y}<extra></extra>",
    )
    figure.update_layout(showlegend=False, hovermode="x unified")
    if x_title:
        figure.update_xaxes(title_text=x_title)
    if y_title:
        figure.update_yaxes(title_text=y_title)
    return figure


def style_subreddit_breakdown_chart(
    figure,
    theme: str = "light",
    x_title: str | None = None,
    y_title: str | None = None,
    hover_label: str | None = None,
):
    figure = style_figure(figure, theme)
    figure.update_traces(
        marker_line_width=0,
        hovertemplate=(
            f"%{{x}}<br>%{{fullData.name}}<br>{hover_label}: %{{y}}<extra></extra>"
            if hover_label
            else "%{x}<br>%{fullData.name}: %{y}<extra></extra>"
        ),
    )
    figure.update_layout(legend_title_text="", title={"pad": {"b": 30}}, legend={"y": 1.01})
    if x_title:
        figure.update_xaxes(title_text=x_title)
    if y_title:
        figure.update_yaxes(title_text=y_title)
    return figure


def style_heatmap_chart(
    figure,
    theme: str = "light",
    x_title: str | None = None,
    y_title: str | None = None,
    colorbar_title: str | None = None,
):
    figure = style_figure(figure, theme)
    figure.update_layout(showlegend=False, hovermode="closest")
    if colorbar_title:
        figure.update_coloraxes(colorbar_title_text=colorbar_title)
    if x_title:
        figure.update_xaxes(title_text=x_title)
    if y_title:
        figure.update_yaxes(title_text=y_title)
    return figure
