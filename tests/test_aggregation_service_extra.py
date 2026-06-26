from __future__ import annotations

from collections import Counter

from reddit_sentiment.services.aggregation_service import AggregationService


def _service() -> AggregationService:
    return AggregationService(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _build_rolling_timeline
# ---------------------------------------------------------------------------


def test_build_rolling_timeline_single_day() -> None:
    service = _service()
    result = service._build_rolling_timeline({"2025-01-01": [1, 3]})

    assert len(result) == 1
    assert result[0]["date"] == "2025-01-01"
    assert result[0]["average_score"] == 2.0


def test_build_rolling_timeline_window_does_not_exceed_three() -> None:
    service = _service()
    daily = {
        "2025-01-01": [10],
        "2025-01-02": [20],
        "2025-01-03": [30],
        "2025-01-04": [40],
    }
    result = service._build_rolling_timeline(daily)

    assert len(result) == 4
    assert result[3]["date"] == "2025-01-04"
    expected = (20 + 30 + 40) / 3
    assert abs(result[3]["average_score"] - expected) < 0.001


def test_build_rolling_timeline_empty() -> None:
    service = _service()
    assert service._build_rolling_timeline({}) == []


# ---------------------------------------------------------------------------
# _build_spike_events
# ---------------------------------------------------------------------------


def test_build_spike_events_detects_volume_spike() -> None:
    service = _service()
    daily_sentiment = {
        "2025-01-01": [0],
        "2025-01-02": [0],
        "2025-01-03": [0],
        "2025-01-04": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    }
    daily_volume: Counter[str] = Counter(
        {
            "2025-01-01": 1,
            "2025-01-02": 1,
            "2025-01-03": 1,
            "2025-01-04": 10,
        }
    )
    result = service._build_spike_events(daily_sentiment, daily_volume)

    spike_dates = [item["date"] for item in result]
    assert "2025-01-04" in spike_dates


def test_build_spike_events_detects_sentiment_shift() -> None:
    service = _service()
    daily_sentiment = {
        "2025-01-01": [0],
        "2025-01-02": [2],
    }
    daily_volume: Counter[str] = Counter({"2025-01-01": 1, "2025-01-02": 1})
    result = service._build_spike_events(daily_sentiment, daily_volume)

    spike_dates = [item["date"] for item in result]
    assert "2025-01-02" in spike_dates


def test_build_spike_events_caps_at_five() -> None:
    service = _service()
    daily_sentiment = {f"2025-01-{i:02d}": [2] for i in range(1, 11)}
    daily_volume: Counter[str] = Counter({f"2025-01-{i:02d}": 100 for i in range(1, 11)})

    result = service._build_spike_events(daily_sentiment, daily_volume)

    assert len(result) <= 5


def test_build_spike_events_empty() -> None:
    service = _service()
    assert service._build_spike_events({}, Counter()) == []


# ---------------------------------------------------------------------------
# _tokenize / _tokenize_phrase
# ---------------------------------------------------------------------------


def test_tokenize_filters_short_tokens() -> None:
    service = _service()
    tokens = service._tokenize("I am a very good product for you")
    assert "I" not in tokens
    assert "am" not in tokens
    assert "very" in tokens
    assert "good" in tokens
    assert "product" in tokens


def test_tokenize_phrase_includes_short_tokens() -> None:
    service = _service()
    tokens = service._tokenize_phrase("big mac is good")
    assert "big" in tokens
    assert "mac" in tokens
    assert "is" in tokens
    assert "good" in tokens


def test_tokenize_strips_leading_trailing_hyphens() -> None:
    service = _service()
    tokens = service._tokenize("-great- product")
    assert "great" in tokens
    assert "product" in tokens


# ---------------------------------------------------------------------------
# _extract_keywords returns empty list for empty text
# ---------------------------------------------------------------------------


def test_extract_keywords_empty_text_returns_empty() -> None:
    service = _service()
    result = service._extract_keywords("", set(), set())
    assert result == []


def test_extract_keywords_all_tokens_excluded_returns_empty() -> None:
    service = _service()
    result = service._extract_keywords("great stuff", {"great", "stuff"}, set())
    assert result == []
