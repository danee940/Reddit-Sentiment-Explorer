from __future__ import annotations

from dataclasses import dataclass

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.sentiment.providers.base import SentimentProvider


@dataclass(frozen=True, slots=True)
class EvaluationSample:
    text: str
    content_language: str
    expected_label: SentimentLabel


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    total_samples: int
    correct_predictions: int
    accuracy: float
    per_label_accuracy: dict[str, float]


DEFAULT_EVALUATION_SAMPLES: tuple[EvaluationSample, ...] = (
    EvaluationSample(
        text="This product is excellent, reliable, and absolutely worth the price.",
        content_language="en",
        expected_label=SentimentLabel.positive,
    ),
    EvaluationSample(
        text="This service is awful, slow, and frustrating to use.",
        content_language="en",
        expected_label=SentimentLabel.negative,
    ),
    EvaluationSample(
        text="Ez a hely nagyon jo, gyors es kedves a kiszolgalas.",
        content_language="hu",
        expected_label=SentimentLabel.positive,
    ),
    EvaluationSample(
        text="Ez nagyon draga es csalodas volt.",
        content_language="hu",
        expected_label=SentimentLabel.negative,
    ),
)


async def evaluate_provider(
    provider: SentimentProvider,
    samples: tuple[EvaluationSample, ...] = DEFAULT_EVALUATION_SAMPLES,
) -> EvaluationResult:
    total_samples = len(samples)
    correct_predictions = 0
    per_label_totals: dict[str, int] = {}
    per_label_correct: dict[str, int] = {}

    for sample in samples:
        prediction = await provider.classify(sample.text, sample.content_language)
        expected_label = sample.expected_label.value
        per_label_totals[expected_label] = per_label_totals.get(expected_label, 0) + 1
        if prediction.label == sample.expected_label:
            correct_predictions += 1
            per_label_correct[expected_label] = per_label_correct.get(expected_label, 0) + 1

    per_label_accuracy = {
        label: per_label_correct.get(label, 0) / total
        for label, total in per_label_totals.items()
        if total
    }
    accuracy = correct_predictions / total_samples if total_samples else 0.0
    return EvaluationResult(
        total_samples=total_samples,
        correct_predictions=correct_predictions,
        accuracy=accuracy,
        per_label_accuracy=per_label_accuracy,
    )
