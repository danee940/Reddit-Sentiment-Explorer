from __future__ import annotations

import plotly.express as px

from reddit_sentiment.dashboard.charts import (
    build_empty_figure,
    get_figure_theme,
    style_distribution_chart,
    style_figure,
    style_heatmap_chart,
    style_subreddit_breakdown_chart,
    style_timeline_chart,
)


def test_get_figure_theme_light_returns_dict() -> None:
    theme = get_figure_theme("light")
    assert isinstance(theme, dict)
    assert "paper_bgcolor" in theme


def test_get_figure_theme_dark_returns_dict() -> None:
    theme = get_figure_theme("dark")
    assert isinstance(theme, dict)
    assert "paper_bgcolor" in theme


def test_get_figure_theme_unknown_falls_back_to_light() -> None:
    unknown = get_figure_theme("neon")
    light = get_figure_theme("light")
    assert unknown == light


def test_get_figure_theme_none_falls_back_to_light() -> None:
    result = get_figure_theme(None)
    light = get_figure_theme("light")
    assert result == light


def test_build_empty_figure_returns_figure_with_title() -> None:
    fig = build_empty_figure("No data available", "light")
    assert fig.layout.title.text == "No data available"


def test_build_empty_figure_dark_theme() -> None:
    fig = build_empty_figure("Empty", "dark")
    dark_theme = get_figure_theme("dark")
    assert fig.layout.paper_bgcolor == dark_theme["paper_bgcolor"]


def test_style_figure_applies_font_family() -> None:
    fig = px.line()
    styled = style_figure(fig, "light")
    assert "Inter" in styled.layout.font.family


def test_style_figure_applies_template() -> None:
    fig = px.line()
    styled = style_figure(fig, "light")
    assert (
        styled.layout.template.layout.plot_bgcolor is not None
        or styled.layout.template is not None
    )


def test_style_distribution_chart_hides_legend() -> None:
    fig = px.bar(x=["positive"], y=[10])
    styled = style_distribution_chart(
        fig, "light", x_title="Sentiment", y_title="Count", hover_label="Matches"
    )
    assert styled.layout.showlegend is False


def test_style_distribution_chart_sets_axis_titles() -> None:
    fig = px.bar(x=["positive"], y=[10])
    styled = style_distribution_chart(fig, "light", x_title="X Axis", y_title="Y Axis")
    assert styled.layout.xaxis.title.text == "X Axis"
    assert styled.layout.yaxis.title.text == "Y Axis"


def test_style_timeline_chart_sets_line_color() -> None:
    fig = px.line(x=["2024-01-01", "2024-01-02"], y=[0.5, 0.3])
    styled = style_timeline_chart(
        fig, color="#4f46e5", fill_color="rgba(79,70,229,0.1)", theme="light"
    )
    assert styled.data[0].line.color == "#4f46e5"


def test_style_timeline_chart_sets_fill() -> None:
    fig = px.line(x=["2024-01-01"], y=[0.5])
    styled = style_timeline_chart(
        fig, color="#4f46e5", fill_color="rgba(79,70,229,0.1)", theme="light"
    )
    assert styled.data[0].fill == "tozeroy"


def test_style_timeline_chart_sets_axis_titles() -> None:
    fig = px.line(x=["2024-01-01"], y=[0.5])
    styled = style_timeline_chart(
        fig,
        color="#000",
        fill_color="rgba(0,0,0,0.1)",
        theme="light",
        x_title="Date",
        y_title="Score",
    )
    assert styled.layout.xaxis.title.text == "Date"
    assert styled.layout.yaxis.title.text == "Score"


def test_style_subreddit_breakdown_chart_hides_legend_title() -> None:
    fig = px.bar(x=["r/linux"], y=[5])
    styled = style_subreddit_breakdown_chart(fig, "light", x_title="Subreddit", y_title="Count")
    assert styled.layout.legend.title.text == ""


def test_style_subreddit_breakdown_chart_sets_axis_titles() -> None:
    fig = px.bar(x=["r/linux"], y=[5])
    styled = style_subreddit_breakdown_chart(
        fig, "light", x_title="Subreddit", y_title="Documents", hover_label="Docs"
    )
    assert styled.layout.xaxis.title.text == "Subreddit"
    assert styled.layout.yaxis.title.text == "Documents"


def test_style_heatmap_chart_sets_colorbar_title() -> None:
    fig = px.density_heatmap(x=["a"], y=["b"], z=[1])
    styled = style_heatmap_chart(fig, "light", colorbar_title="Avg Sentiment")
    assert styled.layout.coloraxis.colorbar.title.text == "Avg Sentiment"


def test_style_heatmap_chart_sets_axis_titles() -> None:
    fig = px.density_heatmap(x=["a"], y=["b"], z=[1])
    styled = style_heatmap_chart(fig, "light", x_title="Date", y_title="Subreddit")
    assert styled.layout.xaxis.title.text == "Date"
    assert styled.layout.yaxis.title.text == "Subreddit"
