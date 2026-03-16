from reddit_sentiment.services.query_service import normalize_term
from reddit_sentiment.services.search_service import SearchService


def test_normalize_term_collapses_spaces() -> None:
    assert normalize_term("  Big   Mac  ") == "big mac"


def test_search_service_phrase_match_is_case_insensitive() -> None:
    service = SearchService("Big Mac")
    matched, match_type, matched_terms, relevance_score = service.match_text(
        "Imadom a big mac menut",
        "body",
    )
    assert matched is True
    assert match_type is not None
    assert matched_terms == ["Big Mac"]
    assert relevance_score == 1.0


def test_search_service_token_fallback_matches_multi_word_terms() -> None:
    service = SearchService("Big Mac")
    matched, match_type, matched_terms, relevance_score = service.match_text(
        "A big burger mint mac legenda",
        "body",
    )
    assert matched is True
    assert match_type is not None
    assert matched_terms == ["big", "mac"]
    assert relevance_score == 0.8


def test_search_service_token_fallback_respects_word_boundaries() -> None:
    service = SearchService("Big Mac")
    matched, match_type, matched_terms, relevance_score = service.match_text(
        "A bigger machine legenda",
        "body",
    )
    assert matched is False
    assert match_type is None
    assert matched_terms == []
    assert relevance_score == 0.0
