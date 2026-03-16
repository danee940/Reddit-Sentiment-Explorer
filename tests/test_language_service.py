from reddit_sentiment.services.language_service import LanguageService


def test_matches_language_accepts_matching_text() -> None:
    service = LanguageService()
    matches, detected_language, confidence = service.matches_language(
        "This is a clearly written English sentence about burgers, fries, and restaurant service.",
        "en",
    )

    assert matches is True
    assert detected_language == "en"
    assert confidence is not None


def test_matches_language_rejects_non_matching_text() -> None:
    service = LanguageService()
    matches, detected_language, confidence = service.matches_language(
        "This is a clearly written English sentence about burgers, fries, and restaurant service.",
        "ru",
    )

    assert matches is False
    assert detected_language == "en"
    assert confidence is not None
