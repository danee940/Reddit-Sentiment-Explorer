from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from reddit_sentiment.dashboard.helpers import (
    api_request,
    format_document_date_bucket,
    format_document_timestamp,
    normalize_timeline_items,
    prepare_document_items,
    sentiment_rank,
    serialize_document_table_rows,
    sort_sentiment_distribution,
)


def test_api_request_returns_parsed_json_on_success() -> None:
    fake_response = MagicMock()
    fake_response.__enter__ = lambda s: s
    fake_response.__exit__ = MagicMock(return_value=False)
    fake_response.read.return_value = b'{"key": "value"}'

    with patch("reddit_sentiment.dashboard.helpers.urlopen", return_value=fake_response):
        result = api_request("GET", "/test")

    assert result == {"key": "value"}


def test_api_request_returns_error_dict_on_http_error_with_json_detail() -> None:
    exc = HTTPError(
        url="http://localhost/test",
        code=422,
        msg="Unprocessable Entity",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(b'{"detail": "bad input value"}'),
    )

    with patch("reddit_sentiment.dashboard.helpers.urlopen", side_effect=exc):
        result = api_request("GET", "/test")

    assert result == {"error": "bad input value"}


def test_api_request_returns_raw_text_on_http_error_with_non_json_detail() -> None:
    exc = HTTPError(
        url="http://localhost/test",
        code=500,
        msg="Internal Server Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(b"plain text error"),
    )

    with patch("reddit_sentiment.dashboard.helpers.urlopen", side_effect=exc):
        result = api_request("GET", "/test")

    assert result == {"error": "plain text error"}


def test_api_request_returns_error_on_http_error_without_detail_in_json() -> None:
    exc = HTTPError(
        url="http://localhost/test",
        code=404,
        msg="Not Found",
        hdrs=None,  # type: ignore[arg-type]
        fp=BytesIO(b'{"message": "not found"}'),
    )

    with patch("reddit_sentiment.dashboard.helpers.urlopen", side_effect=exc):
        result = api_request("GET", "/test")

    assert "error" in result


def test_api_request_returns_error_dict_on_url_error() -> None:
    with patch(
        "reddit_sentiment.dashboard.helpers.urlopen", side_effect=URLError("no route to host")
    ):
        result = api_request("GET", "/test")

    assert "error" in result
    assert "no route to host" in result["error"]


def test_sentiment_rank_known_label() -> None:
    assert sentiment_rank("very_negative") < sentiment_rank("negative")
    assert sentiment_rank("negative") < sentiment_rank("neutral")


def test_sentiment_rank_unknown_label() -> None:
    known_max = sentiment_rank("very_negative")
    unknown = sentiment_rank("totally_unknown")
    assert unknown > known_max


def test_sort_sentiment_distribution_orders_correctly() -> None:
    items = [
        {"label": "neutral", "count": 3},
        {"label": "very_positive", "count": 1},
        {"label": "very_negative", "count": 2},
    ]
    result = sort_sentiment_distribution(items)
    labels = [item["label"] for item in result]
    assert labels.index("very_negative") < labels.index("neutral")
    assert labels.index("neutral") < labels.index("very_positive")


def test_normalize_timeline_items_sorts_by_key() -> None:
    items = [{"date": "2024-03-01"}, {"date": "2024-01-01"}, {"date": "2024-02-01"}]
    result = normalize_timeline_items(items, "date")
    assert result[0]["date"] == "2024-01-01"
    assert result[-1]["date"] == "2024-03-01"


def test_format_document_timestamp_none_returns_unknown() -> None:
    result = format_document_timestamp(None, "en")
    assert result  # not empty


def test_format_document_timestamp_formats_value() -> None:
    result = format_document_timestamp("2024-01-15T10:30:00Z", "en")
    assert "2024-01-15" in result
    assert "UTC" in result


def test_format_document_date_bucket_none_returns_none() -> None:
    assert format_document_date_bucket(None) is None


def test_format_document_date_bucket_from_iso() -> None:
    result = format_document_date_bucket("2024-01-15T10:30:00")
    assert result == "2024-01-15"


def test_format_document_date_bucket_from_space_separated() -> None:
    result = format_document_date_bucket("2024-01-15 10:30:00")
    assert result == "2024-01-15"


def test_format_document_date_bucket_plain_date_passthrough() -> None:
    result = format_document_date_bucket("2024-01-15")
    assert result == "2024-01-15"


def test_prepare_document_items_adds_display_fields() -> None:
    items = [
        {
            "document_id": "doc-1",
            "content": "hello world",
            "created_utc": "2024-01-15T10:00:00Z",
            "sentiment_label": "positive",
        }
    ]
    result = prepare_document_items(items, "en")
    assert len(result) == 1
    assert result[0]["id"] == "doc-1"
    assert "display_date" in result[0]
    assert "date_bucket" in result[0]
    assert "snippet_preview" in result[0]
    assert "sentiment_text" in result[0]


def test_prepare_document_items_truncates_long_content() -> None:
    long_text = "x" * 300
    items = [
        {"document_id": "d1", "content": long_text, "created_utc": None, "sentiment_label": None}
    ]
    result = prepare_document_items(items, "en")
    assert len(result[0]["snippet_preview"]) <= 180


def test_serialize_document_table_rows_converts_lists() -> None:
    items = [{"tags": ["a", "b"], "score": 5}]
    result = serialize_document_table_rows(items)
    assert result[0]["tags"] == "a, b"
    assert result[0]["score"] == 5


def test_serialize_document_table_rows_converts_dicts() -> None:
    items = [{"meta": {"key": "val"}}]
    result = serialize_document_table_rows(items)
    assert result[0]["meta"] == '{"key": "val"}'


def test_serialize_document_table_rows_converts_nested_list_of_dicts() -> None:
    items = [{"phrases": [{"term": "hello", "count": 2}]}]
    result = serialize_document_table_rows(items)
    assert json.loads(result[0]["phrases"]) == [{"term": "hello", "count": 2}]
