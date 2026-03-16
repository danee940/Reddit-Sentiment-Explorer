from collections import Counter

from reddit_sentiment.core.languages import SUPPORTED_CONTENT_LANGUAGES
from reddit_sentiment.core.stop_words import (
    GLOBAL_STOP_WORDS,
    LANGUAGE_STOP_WORDS,
    get_stop_words_for_language,
)
from reddit_sentiment.dashboard.components import build_document_detail
from reddit_sentiment.services.aggregation_service import AggregationService


def test_extract_keywords_excludes_query_terms_and_prefers_phrases() -> None:
    service = AggregationService(None)  # type: ignore[arg-type]

    keywords = service._extract_keywords(
        "Magyar Péter kampány beszéd kampány beszéd kampány beszéd és hosszú vita.",
        {"magyar", "péter"},
        {"és"},
    )

    assert "magyar" not in keywords
    assert "péter" not in keywords
    assert "kampány beszéd" in keywords


def test_extract_evidence_terms_prefers_grounded_phrases() -> None:
    service = AggregationService(None)  # type: ignore[arg-type]

    evidence_terms = service._extract_evidence_terms(
        [
            "battery dies in a few hours",
            "gets hot while charging",
            "iPhone battery dies fast",
        ],
        {"iphone"},
        {"while"},
    )

    assert "battery dies in a" in evidence_terms
    assert "gets hot charging" in evidence_terms
    assert all("iphone" not in term for term in evidence_terms)


def test_stop_words_cover_all_supported_content_languages() -> None:
    assert SUPPORTED_CONTENT_LANGUAGES.issubset(set(LANGUAGE_STOP_WORDS))


def test_get_stop_words_uses_selected_language_only() -> None:
    en_words = get_stop_words_for_language("en")
    hu_words = get_stop_words_for_language("hu")
    ru_words = get_stop_words_for_language("ru")

    assert "this" in en_words
    assert "this" not in hu_words
    assert "hogy" in hu_words
    assert "hogy" not in en_words
    assert "http" in ru_words
    assert "this" not in ru_words
    assert GLOBAL_STOP_WORDS.issubset(ru_words)


def test_build_phrase_breakdown_orders_best_to_worst() -> None:
    service = AggregationService(None)  # type: ignore[arg-type]

    phrase_breakdown = service._build_phrase_breakdown(
        {
            "negative": Counter({"bad battery": 2}),
            "very_positive": Counter({"love it": 3}),
            "neutral": Counter({"works okay": 1}),
            "very_negative": Counter({"completely unusable": 4}),
            "positive": Counter({"pretty good": 2}),
        }
    )

    assert [item["label"] for item in phrase_breakdown] == [
        "very_positive",
        "positive",
        "neutral",
        "negative",
        "very_negative",
    ]


def test_build_document_detail_wraps_long_confidence_label() -> None:
    detail = build_document_detail(
        {
            "subreddit": "hungary",
            "display_date": "2026-03-16 09:43:38 UTC",
            "sentiment_label": "very_negative",
            "source_type": "comment",
            "score": 1,
            "sentiment_confidence": 0.95,
            "content": "Example content",
            "sentiment_rationale": "Example rationale",
            "sentiment_evidence_phrases": ["battery dies fast"],
            "permalink": "https://reddit.com/example",
        },
        "hu",
    )

    confidence_card = detail.children[1].children[2]
    confidence_label = confidence_card.children[0]

    assert "min-w-0" in confidence_card.className
    assert "whitespace-normal" in confidence_label.className
    assert confidence_label.style["hyphens"] == "auto"
    assert confidence_label.style["overflowWrap"] == "normal"
    assert confidence_label.style["wordBreak"] == "normal"
