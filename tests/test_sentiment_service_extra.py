from __future__ import annotations

from dataclasses import dataclass, field

from reddit_sentiment.core.config import Settings
from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.sentiment.providers.base import (
    MOCK_PROVIDER_VERSION,
    XLM_ROBERTA_PROVIDER_VERSION,
    SentimentPrediction,
    get_openai_provider_version,
)
from reddit_sentiment.services.sentiment_service import SentimentService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class DocumentStub:
    id: str
    full_text: str


@dataclass
class QueryRunStub:
    id: str
    language_filter: str


def _make_prediction(
    label: SentimentLabel = SentimentLabel.neutral,
    score_value: int = 0,
    confidence: float | None = 0.9,
    rationale: str | None = None,
    evidence_phrases: list[str] | None = None,
) -> SentimentPrediction:
    return SentimentPrediction(
        label=label,
        score_value=score_value,
        confidence=confidence,
        rationale=rationale,
        evidence_phrases=evidence_phrases or [],
        provider_name="mock",
        provider_version=MOCK_PROVIDER_VERSION,
    )


def _build_service_with_settings(settings: Settings) -> SentimentService:
    session_stub = object()
    return SentimentService(session=session_stub, settings=settings)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


def test_provider_selection_defaults_to_mock() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="", llm_model="gpt-4o-mini")
    service = _build_service_with_settings(settings)

    assert service.provider_name == "mock"
    assert service.provider_version == MOCK_PROVIDER_VERSION


def test_provider_selection_openai_requires_api_key() -> None:
    settings = Settings(sentiment_provider="openai", llm_api_key="", llm_model="gpt-4o-mini")
    service = _build_service_with_settings(settings)

    assert service.provider_name == "mock"


def test_provider_selection_openai_with_api_key() -> None:
    settings = Settings(
        sentiment_provider="openai", llm_api_key="sk-test", llm_model="gpt-4o-mini"
    )
    service = _build_service_with_settings(settings)

    assert service.provider_name == "openai"
    assert service.provider_version == get_openai_provider_version("gpt-4o-mini")


def test_provider_selection_xlm_roberta() -> None:
    settings = Settings(sentiment_provider="xlm_roberta", llm_api_key="", llm_model="gpt-4o-mini")
    service = _build_service_with_settings(settings)

    assert service.provider_name == "xlm_roberta"
    assert service.provider_version == XLM_ROBERTA_PROVIDER_VERSION


# ---------------------------------------------------------------------------
# _normalize_rationale
# ---------------------------------------------------------------------------


def _rationale_service(threshold: float = 0.6) -> SentimentService:
    settings = Settings(
        sentiment_provider="mock",
        llm_api_key="",
        sentiment_confidence_threshold=threshold,
    )
    return _build_service_with_settings(settings)


def test_normalize_rationale_returns_rationale_when_confidence_above_threshold() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale("good product", 0.9, "en")
    assert result == "good product"


def test_normalize_rationale_returns_rationale_when_confidence_equals_threshold() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale("good product", 0.6, "en")
    assert result == "good product"


def test_normalize_rationale_prepends_low_confidence_prefix_for_en() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale("decent", 0.4, "en")
    assert result is not None
    assert "Low-confidence result" in result
    assert "0.40" in result
    assert "decent" in result


def test_normalize_rationale_prepends_low_confidence_prefix_for_hu() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale(None, 0.3, "hu")
    assert result is not None
    assert "Alacsony bizonyosságú" in result


def test_normalize_rationale_prepends_low_confidence_prefix_for_ru() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale(None, 0.3, "ru")
    assert result is not None
    assert "Результат с низкой уверенностью" in result


def test_normalize_rationale_returns_original_for_unknown_language_low_confidence() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale("something", 0.1, "de")
    assert result == "something"


def test_normalize_rationale_returns_none_confidence_passes_threshold() -> None:
    service = _rationale_service(threshold=0.6)
    result = service._normalize_rationale(None, None, "en")
    assert result is None


# ---------------------------------------------------------------------------
# _normalize_evidence_phrases
# ---------------------------------------------------------------------------


def _evidence_service() -> SentimentService:
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    return _build_service_with_settings(settings)


def test_normalize_evidence_phrases_filters_short_phrases() -> None:
    service = _evidence_service()
    text = "good battery life is great"
    result = service._normalize_evidence_phrases(["ok", "hi", "good battery life"], text)
    assert "ok" not in result
    assert "hi" not in result
    assert "good battery life" in result


def test_normalize_evidence_phrases_filters_phrases_not_in_text() -> None:
    service = _evidence_service()
    result = service._normalize_evidence_phrases(
        ["battery life", "completely made up phrase xyz"],
        "battery life is great",
    )
    assert "battery life" in result
    assert "completely made up phrase xyz" not in result


def test_normalize_evidence_phrases_deduplicates() -> None:
    service = _evidence_service()
    result = service._normalize_evidence_phrases(
        ["battery life", "battery life", "great product"],
        "battery life is a great product",
    )
    assert result.count("battery life") == 1


def test_normalize_evidence_phrases_caps_at_three() -> None:
    service = _evidence_service()
    text = "battery life good build quality fast charging awesome screen"
    result = service._normalize_evidence_phrases(
        ["battery life", "good build", "fast charging", "awesome screen"],
        text,
    )
    assert len(result) <= 3


def test_normalize_evidence_phrases_empty_input() -> None:
    service = _evidence_service()
    result = service._normalize_evidence_phrases([], "some text here")
    assert result == []


# ---------------------------------------------------------------------------
# _persist_reused_result
# ---------------------------------------------------------------------------


def test_persist_reused_result_copies_fields() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="")

    class FakeSession:
        added: list = []

        def add(self, obj):
            self.added.append(obj)

    session = FakeSession()
    service = SentimentService(session=session, settings=settings)  # type: ignore[arg-type]

    @dataclass
    class FakeSentimentResult:
        query_run_id: str = "old-run"
        document_id: str = "doc-1"
        provider_name: str = "mock"
        provider_version: str = MOCK_PROVIDER_VERSION
        label: SentimentLabel = SentimentLabel.positive
        score_value: int = 1
        confidence: float | None = 0.9
        rationale: str | None = "good"
        evidence_phrases: list = field(default_factory=list)

    reusable = FakeSentimentResult()
    query_run = QueryRunStub(id="new-run", language_filter="en")
    document = DocumentStub(id="doc-1", full_text="great product")

    result = service._persist_reused_result(query_run, document, reusable)  # type: ignore[arg-type]

    assert result.query_run_id == "new-run"
    assert result.document_id == "doc-1"
    assert result.label == SentimentLabel.positive
    assert result in session.added


# ---------------------------------------------------------------------------
# _get_provider_version
# ---------------------------------------------------------------------------


def test_get_provider_version_mock() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    service = _build_service_with_settings(settings)
    assert service._get_provider_version("mock") == MOCK_PROVIDER_VERSION


def test_get_provider_version_xlm_roberta() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="")
    service = _build_service_with_settings(settings)
    assert service._get_provider_version("xlm_roberta") == XLM_ROBERTA_PROVIDER_VERSION


def test_get_provider_version_openai() -> None:
    settings = Settings(sentiment_provider="mock", llm_api_key="", llm_model="gpt-4o-mini")
    service = _build_service_with_settings(settings)
    assert service._get_provider_version("openai") == get_openai_provider_version("gpt-4o-mini")
