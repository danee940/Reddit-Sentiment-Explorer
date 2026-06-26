from __future__ import annotations

from dash import html

from reddit_sentiment.dashboard.components.base import build_sentiment_badge, metric_card
from reddit_sentiment.dashboard.helpers import prepare_document_items


def _sample_item() -> dict:
    raw = [
        {
            "document_id": "doc-1",
            "subreddit": "hungary",
            "sentiment_label": "positive",
            "source_type": "post",
            "created_utc": "2024-01-15T10:00:00Z",
            "score": 42,
            "content": "This is a great product with excellent quality and performance.",
            "snippet": "This is a great product",
            "permalink": "https://reddit.com/r/hungary/comments/abc/title/",
            "sentiment_confidence": 0.92,
            "sentiment_rationale": "Positive sentiment detected",
            "sentiment_evidence_phrases": ["great product", "excellent quality"],
        }
    ]
    return prepare_document_items(raw, "en")[0]


def test_metric_card_contains_label_and_value() -> None:
    card = metric_card("Documents", "42")
    json_repr = str(card.to_plotly_json())
    assert "Documents" in json_repr
    assert "42" in json_repr


def test_metric_card_returns_html_div() -> None:
    card = metric_card("Score", "0.75")
    assert isinstance(card, html.Div)


def test_build_sentiment_badge_known_label() -> None:
    span = build_sentiment_badge("positive", "en")
    class_name = span.to_plotly_json()["props"]["className"]
    assert "sentiment-badge--positive" in class_name


def test_build_sentiment_badge_very_positive() -> None:
    span = build_sentiment_badge("very_positive", "en")
    class_name = span.to_plotly_json()["props"]["className"]
    assert "sentiment-badge--very-positive" in class_name


def test_build_sentiment_badge_unknown_label_falls_back_to_unscored() -> None:
    span = build_sentiment_badge("completely_unknown_label", "en")
    class_name = span.to_plotly_json()["props"]["className"]
    assert "sentiment-badge--unscored" in class_name


def test_build_sentiment_badge_none_label_uses_unscored() -> None:
    span = build_sentiment_badge(None, "en")
    class_name = span.to_plotly_json()["props"]["className"]
    assert "sentiment-badge--unscored" in class_name


def test_build_document_detail_with_item_contains_subreddit() -> None:
    from reddit_sentiment.dashboard.components import build_document_detail

    item = _sample_item()
    result = build_document_detail(item, "en")
    json_str = str(result.to_plotly_json())
    assert "hungary" in json_str


def test_build_document_detail_with_none_returns_div() -> None:
    from reddit_sentiment.dashboard.components import build_document_detail

    result = build_document_detail(None, "en")
    assert isinstance(result, html.Div)


def test_build_document_detail_with_permalink_contains_link() -> None:
    from reddit_sentiment.dashboard.components import build_document_detail

    item = _sample_item()
    result = build_document_detail(item, "en")
    json_str = str(result.to_plotly_json())
    assert "reddit.com" in json_str


def test_build_documents_table_returns_data_table() -> None:
    from reddit_sentiment.dashboard.components.documents import build_documents_table

    items = [_sample_item()]
    table = build_documents_table(items, "light", "en")
    assert type(table).__name__ == "DataTable"


def test_build_documents_table_empty_items() -> None:
    from reddit_sentiment.dashboard.components.documents import build_documents_table

    table = build_documents_table([], "light", "en")
    assert type(table).__name__ == "DataTable"


def test_build_documents_layout_with_items_returns_div() -> None:
    from reddit_sentiment.dashboard.components.documents import build_documents_layout

    items = [_sample_item()]
    placeholder = html.Div("detail here")
    result = build_documents_layout(items, "light", "en", placeholder)
    assert isinstance(result, html.Div)
    json_str = str(result.to_plotly_json())
    assert "document-subreddit-filter" in json_str


def test_build_documents_layout_empty_items_returns_div() -> None:
    from reddit_sentiment.dashboard.components.documents import build_documents_layout

    placeholder = html.Div("no doc")
    result = build_documents_layout([], "light", "en", placeholder)
    assert isinstance(result, html.Div)
