from reddit_sentiment.sentiment.providers.openai_provider import OpenAISentimentProvider


def test_normalize_confidence_accepts_named_levels() -> None:
    assert OpenAISentimentProvider._normalize_confidence("high") == 0.8
    assert OpenAISentimentProvider._normalize_confidence("medium") == 0.5
    assert OpenAISentimentProvider._normalize_confidence("very_high") == 0.95


def test_normalize_confidence_accepts_numeric_values() -> None:
    assert OpenAISentimentProvider._normalize_confidence("0.67") == 0.67
    assert OpenAISentimentProvider._normalize_confidence(0.42) == 0.42
    assert OpenAISentimentProvider._normalize_confidence(None) is None
