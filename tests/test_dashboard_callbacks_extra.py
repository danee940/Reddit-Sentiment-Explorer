from __future__ import annotations

from unittest.mock import MagicMock, patch

from dash import html, no_update

from reddit_sentiment.dashboard.callbacks import documents as doc_callbacks
from reddit_sentiment.dashboard.callbacks import results as results_callbacks
from reddit_sentiment.dashboard.callbacks import theme_language as tl_callbacks  # noqa: E402

# ---------------------------------------------------------------------------
# documents callbacks
# ---------------------------------------------------------------------------


def test_render_document_detail_empty_rows_returns_div() -> None:
    result = doc_callbacks.render_document_detail([], None, None, "en")
    assert isinstance(result, html.Div)


def test_render_document_detail_uses_active_cell_row_id() -> None:
    items = [
        {
            "id": "doc-1",
            "subreddit": "hungary",
            "sentiment_label": "positive",
            "source_type": "post",
            "created_utc": "2024-01-01T10:00:00Z",
            "score": 5,
            "content": "hello",
            "permalink": None,
            "sentiment_confidence": 0.9,
            "sentiment_rationale": None,
            "sentiment_evidence_phrases": [],
            "display_date": "2024-01-01",
            "date_bucket": "2024-01-01",
            "snippet_preview": "hello",
            "sentiment_text": "Positive",
        }
    ]
    result = doc_callbacks.render_document_detail(items, None, {"row_id": "doc-1"}, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "hungary" in json_str


def test_render_document_detail_uses_selected_row_ids() -> None:
    items = [
        {
            "id": "doc-1",
            "subreddit": "linux",
            "sentiment_label": "neutral",
            "source_type": "comment",
            "created_utc": "2024-01-01T10:00:00Z",
            "score": 1,
            "content": "some text",
            "permalink": None,
            "sentiment_confidence": 0.85,
            "sentiment_rationale": None,
            "sentiment_evidence_phrases": [],
            "display_date": "2024-01-01",
            "date_bucket": "2024-01-01",
            "snippet_preview": "some text",
            "sentiment_text": "Neutral",
        }
    ]
    result = doc_callbacks.render_document_detail(items, ["doc-1"], None, "en")
    assert isinstance(result, html.Div)


def test_render_document_detail_falls_back_to_first_row_when_no_match() -> None:
    items = [
        {
            "id": "doc-99",
            "subreddit": "rust",
            "sentiment_label": "positive",
            "source_type": "post",
            "created_utc": "2024-01-01T10:00:00Z",
            "score": 10,
            "content": "great",
            "permalink": None,
            "sentiment_confidence": 0.8,
            "sentiment_rationale": None,
            "sentiment_evidence_phrases": [],
            "display_date": "2024-01-01",
            "date_bucket": "2024-01-01",
            "snippet_preview": "great",
            "sentiment_text": "Positive",
        }
    ]
    result = doc_callbacks.render_document_detail(items, ["non-existent-id"], None, "en")
    assert isinstance(result, html.Div)


def test_sync_selected_row_none_active_cell_returns_empty() -> None:
    assert doc_callbacks.sync_selected_row_from_active_cell(None, [{"id": "doc-1"}]) == []


def test_sync_selected_row_missing_row_key_returns_empty() -> None:
    assert doc_callbacks.sync_selected_row_from_active_cell({}, [{"id": "doc-1"}]) == []


def test_sync_selected_row_returns_row_id() -> None:
    result = doc_callbacks.sync_selected_row_from_active_cell({"row": 0}, [{"id": "doc-1"}])
    assert result == ["doc-1"]


def test_sync_selected_row_out_of_bounds_returns_empty() -> None:
    result = doc_callbacks.sync_selected_row_from_active_cell({"row": 10}, [{"id": "doc-1"}])
    assert result == []


def test_toggle_clear_filters_disabled_when_all_none() -> None:
    assert doc_callbacks.toggle_clear_filters_button(None, None, None, None, None) is True


def test_toggle_clear_filters_disabled_when_empty_search() -> None:
    assert doc_callbacks.toggle_clear_filters_button(None, None, None, None, "  ") is True


def test_toggle_clear_filters_enabled_when_date_set() -> None:
    assert doc_callbacks.toggle_clear_filters_button("2024-01-01", None, None, None, None) is False


def test_toggle_clear_filters_enabled_when_subreddit_set() -> None:
    assert doc_callbacks.toggle_clear_filters_button(None, "hungary", None, None, None) is False


def test_sync_filters_clear_button_resets_all() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "clear-chart-filters-button"

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(None, None, None, None, 1)

    assert result == (None, None, None, None, "")


def test_sync_filters_sentiment_timeline_click_sets_date() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "sentiment-timeline-chart"
    click_data = {"points": [{"x": "2024-01-15"}]}

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(click_data, None, None, None, None)

    assert result[0] == "2024-01-15"
    assert result[1] is no_update


def test_sync_filters_volume_chart_click_sets_date() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "volume-chart"
    click_data = {"points": [{"x": "2024-03-10"}]}

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(None, click_data, None, None, None)

    assert result[0] == "2024-03-10"


def test_sync_filters_subreddit_chart_click_sets_subreddit() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "subreddit-chart"
    click_data = {"points": [{"x": "hungary"}]}

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(None, None, click_data, None, None)

    assert result[1] == "hungary"
    assert result[0] is no_update


def test_sync_filters_distribution_chart_click_sets_sentiment() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "sentiment-distribution-chart"
    click_data = {"points": [{"customdata": ["positive"]}]}

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(None, None, None, click_data, None)

    assert result[2] == "positive"
    assert result[0] is no_update


def test_sync_filters_no_points_returns_no_update() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "sentiment-timeline-chart"
    click_data: dict = {"points": []}

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(click_data, None, None, None, None)

    assert all(r is no_update for r in result)


def test_sync_filters_unknown_trigger_returns_no_update() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "some-other-element"

    with patch("reddit_sentiment.dashboard.callbacks.documents.ctx", fake_ctx):
        result = doc_callbacks.sync_filters_from_chart_clicks(None, None, None, None, None)

    assert all(r is no_update for r in result)


# ---------------------------------------------------------------------------
# theme_language callbacks
# ---------------------------------------------------------------------------


def test_update_content_language_store_normalizes_en() -> None:
    result = tl_callbacks.update_content_language_store("en")
    assert result == "en"


def test_update_content_language_store_normalizes_hu() -> None:
    result = tl_callbacks.update_content_language_store("hu")
    assert result == "hu"


def test_update_content_language_store_none_returns_default() -> None:
    result = tl_callbacks.update_content_language_store(None)
    assert result  # should return a non-empty string


def test_update_active_tab_store_returns_no_update_for_none() -> None:
    result = tl_callbacks.update_active_tab_store(None)
    assert result is no_update


def test_update_active_tab_store_returns_value_for_valid_tab() -> None:
    result = tl_callbacks.update_active_tab_store("search-overview")
    assert result == "search-overview"


def test_update_active_tab_store_returns_no_update_for_invalid_tab() -> None:
    result = tl_callbacks.update_active_tab_store("not-a-valid-tab")
    assert result is no_update


def test_render_static_content_returns_tuple() -> None:
    result = tl_callbacks.render_static_content("en", "light", "en")
    assert len(result) >= 14


def test_render_static_content_hu_language() -> None:
    result = tl_callbacks.render_static_content("hu", "dark", "hu")
    assert len(result) >= 14


def test_update_theme_store_returns_light_when_light_triggered() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "theme-toggle-light"

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        result = tl_callbacks.update_theme_store(1, None, "dark")

    assert result == "light"


def test_update_theme_store_returns_dark_when_dark_triggered() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "theme-toggle-dark"

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        result = tl_callbacks.update_theme_store(None, 1, "light")

    assert result == "dark"


def test_update_theme_store_falls_back_to_normalized_current() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "something-else"

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        result = tl_callbacks.update_theme_store(None, None, "dark")

    assert result == "dark"


def test_update_language_store_returns_en_when_en_triggered() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "language-toggle-en"

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        result = tl_callbacks.update_language_store(1, None, "hu")

    assert result == "en"


def test_update_language_store_returns_hu_when_hu_triggered() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "language-toggle-hu"

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        result = tl_callbacks.update_language_store(None, 1, "en")

    assert result == "hu"


def test_update_language_store_falls_back_to_current() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "other"

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        result = tl_callbacks.update_language_store(None, None, "hu")

    assert result == "hu"


def test_update_subreddit_store_add_new_subreddit() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "add-subreddit-button"
    fake_ctx.triggered = [{"value": 1}]

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        names, input_val, feedback = tl_callbacks.update_subreddit_store(
            1, None, None, "en", "linux", ["hungary"], None
        )

    assert "linux" in names  # type: ignore[operator]
    assert "hungary" in names  # type: ignore[operator]


def test_update_subreddit_store_duplicate_returns_no_update() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "add-subreddit-button"
    fake_ctx.triggered = [{"value": 1}]

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        names, input_val, feedback = tl_callbacks.update_subreddit_store(
            1, None, None, "en", "hungary", ["hungary"], None
        )

    assert names is no_update


def test_update_subreddit_store_empty_input_returns_no_update() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "add-subreddit-button"
    fake_ctx.triggered = [{"value": 1}]

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        names, input_val, feedback = tl_callbacks.update_subreddit_store(
            1, None, None, "en", "   ", ["hungary"], None
        )

    assert names is no_update


def test_update_subreddit_store_remove_subreddit() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = {"type": "remove-subreddit", "name": "linux"}
    fake_ctx.triggered = [{"value": 1}]

    remove_ids = [{"type": "remove-subreddit", "name": "linux"}]

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        names, input_val, feedback = tl_callbacks.update_subreddit_store(
            None, None, [1], "en", None, ["hungary", "linux"], remove_ids
        )

    assert "linux" not in names  # type: ignore[operator]
    assert "hungary" in names  # type: ignore[operator]


def test_update_subreddit_store_unknown_trigger_returns_no_update() -> None:
    fake_ctx = MagicMock()
    fake_ctx.triggered_id = "some-other-button"
    fake_ctx.triggered = []

    with patch("reddit_sentiment.dashboard.callbacks.theme_language.ctx", fake_ctx):
        names, input_val, feedback = tl_callbacks.update_subreddit_store(
            None, None, None, "en", None, ["hungary"], None
        )

    assert names is no_update
    assert feedback == ""


def test_validate_subreddit_list_empty_returns_empty_result() -> None:
    result = tl_callbacks.validate_subreddit_list(None)
    assert result == {"names": [], "items": [], "error": None}


def test_validate_subreddit_list_calls_api_and_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(
        tl_callbacks,
        "api_request",
        lambda method, path, payload=None: {
            "items": [{"name": "hungary", "exists": True}]
        },
    )
    result = tl_callbacks.validate_subreddit_list(["hungary"])
    assert result["names"] == ["hungary"]
    assert result["items"][0]["exists"] is True  # type: ignore[index]
    assert result["error"] is None


def test_render_subreddit_list_returns_html_div() -> None:
    result = tl_callbacks.render_subreddit_list(["hungary"], None, "en")
    assert isinstance(result, html.Div)


def test_render_search_history_returns_html_div() -> None:
    result = tl_callbacks.render_search_history(None, None, "en")
    assert isinstance(result, html.Div)


def test_render_tabs_returns_component() -> None:
    from dash import dcc

    result = tl_callbacks.render_tabs("en", None)
    assert isinstance(result, dcc.Tabs)


# ---------------------------------------------------------------------------
# results callbacks
# ---------------------------------------------------------------------------


def test_build_distribution_chart_empty_returns_figure() -> None:
    fig = results_callbacks._build_distribution_chart([], "en", "light")
    assert hasattr(fig, "update_layout")


def test_build_timeline_chart_empty_returns_figure() -> None:
    fig = results_callbacks._build_timeline_chart(
        [], "sentiment_timeline", "#4f46e5", "rgba(79,70,229,0.1)", "en", "light",
        "no_timeline_data",
    )
    assert hasattr(fig, "update_layout")


def test_build_volume_chart_empty_returns_figure() -> None:
    fig = results_callbacks._build_volume_chart([], "en", "light")
    assert hasattr(fig, "update_layout")


def test_build_heatmap_chart_empty_returns_figure() -> None:
    fig = results_callbacks._build_heatmap_chart([], "en", "light")
    assert hasattr(fig, "update_layout")


def test_build_subreddit_chart_empty_returns_figure() -> None:
    fig = results_callbacks._build_subreddit_chart([], "en", "light")
    assert hasattr(fig, "update_layout")


def test_build_phrase_breakdown_empty_returns_html_div() -> None:
    result = results_callbacks._build_phrase_breakdown([], "en")
    assert isinstance(result, html.Div)


def test_build_phrase_breakdown_with_data_returns_html_div() -> None:
    data = [{"label": "positive", "terms": [{"term": "great", "count": 5}]}]
    result = results_callbacks._build_phrase_breakdown(data, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "great" in json_str


def test_build_spike_events_empty_returns_html_div() -> None:
    result = results_callbacks._build_spike_events([], "en")
    assert isinstance(result, html.Div)


def test_build_spike_events_with_data_returns_html_div() -> None:
    data = [{"date": "2024-01-15", "count": 10, "average_score": 0.8, "score_change": 0.5}]
    result = results_callbacks._build_spike_events(data, "en")
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "2024-01-15" in json_str


def test_render_results_none_store_returns_11_items(monkeypatch) -> None:
    monkeypatch.setattr(results_callbacks, "api_request", lambda *a, **kw: {})
    result = results_callbacks.render_results(None, "light", "en")
    assert len(result) == 11


def test_render_results_pending_does_not_call_api(monkeypatch) -> None:
    calls: list[int] = []

    def tracking_api(*a: object, **kw: object) -> dict:
        calls.append(1)
        return {}

    monkeypatch.setattr(results_callbacks, "api_request", tracking_api)

    results_callbacks.render_results(
        {"status": "running", "query_run_id": "r-1", "term": "foo", "subreddits": ["linux"]},
        "light",
        "en",
    )
    assert calls == []


def test_render_results_completed_calls_api_and_returns_11(monkeypatch) -> None:
    charts_payload = {
        "overview": {
            "total_documents": 5,
            "average_score": 0.3,
            "high_confidence_documents": 4,
            "low_confidence_documents": 1,
        },
        "sentiment_distribution": [],
        "sentiment_timeline": [],
        "rolling_sentiment_timeline": [],
        "volume_timeline": [],
        "sentiment_heatmap": [],
        "subreddit_breakdown": [],
        "phrase_breakdown": [],
        "spike_events": [],
    }
    documents_payload: dict = {"items": []}

    def fake_api(method: str, path: str, payload: dict | None = None) -> dict:
        if "charts" in path:
            return charts_payload
        return documents_payload

    monkeypatch.setattr(results_callbacks, "api_request", fake_api)

    result = results_callbacks.render_results(
        {
            "status": "completed",
            "query_run_id": "r-1",
            "subreddits": ["hungary"],
            "term": "linux",
        },
        "light",
        "en",
    )
    assert len(result) == 11
