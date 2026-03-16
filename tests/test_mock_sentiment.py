import pytest

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.sentiment.providers.mock import MockSentimentProvider


@pytest.mark.asyncio
async def test_mock_sentiment_returns_positive_label() -> None:
    provider = MockSentimentProvider()
    prediction = await provider.classify("Ez nagyon jo es remek valasztas.", "hu")
    assert prediction.label in {SentimentLabel.positive, SentimentLabel.very_positive}
    assert prediction.score_value > 0
    assert prediction.evidence_phrases


@pytest.mark.asyncio
async def test_mock_sentiment_returns_negative_label() -> None:
    provider = MockSentimentProvider()
    prediction = await provider.classify("Ez szornyu, rossz es draga.", "hu")
    assert prediction.label in {SentimentLabel.negative, SentimentLabel.very_negative}
    assert prediction.score_value < 0
    assert prediction.evidence_phrases


@pytest.mark.asyncio
async def test_mock_sentiment_supports_english_queries() -> None:
    provider = MockSentimentProvider()
    prediction = await provider.classify("This is a great, amazing, excellent choice.", "en")
    assert prediction.label in {SentimentLabel.positive, SentimentLabel.very_positive}
    assert prediction.score_value > 0


@pytest.mark.asyncio
async def test_mock_sentiment_supports_russian_queries() -> None:
    provider = MockSentimentProvider()
    prediction = await provider.classify("Это ужасно и очень плохо.", "ru")
    assert prediction.label in {SentimentLabel.negative, SentimentLabel.very_negative}
    assert prediction.score_value < 0
