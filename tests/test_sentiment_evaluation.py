import pytest

from reddit_sentiment.sentiment.evaluation import DEFAULT_EVALUATION_SAMPLES, evaluate_provider
from reddit_sentiment.sentiment.providers.mock import MockSentimentProvider


@pytest.mark.asyncio
async def test_evaluate_provider_reports_accuracy_breakdown() -> None:
    result = await evaluate_provider(MockSentimentProvider(), DEFAULT_EVALUATION_SAMPLES)

    assert result.total_samples == len(DEFAULT_EVALUATION_SAMPLES)
    assert 0.0 <= result.accuracy <= 1.0
    assert "positive" in result.per_label_accuracy
    assert "negative" in result.per_label_accuracy
