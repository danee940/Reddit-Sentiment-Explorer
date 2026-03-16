from reddit_sentiment.services.subreddit_service import SubredditService


def test_normalize_name_strips_prefixes_and_case() -> None:
    assert SubredditService.normalize_name(" r/Hungary ") == "hungary"
    assert SubredditService.normalize_name("/r/AskHungary/") == "askhungary"
    assert SubredditService.normalize_name("https://www.reddit.com/r/Budapest/") == "budapest"


def test_normalize_names_discards_empty_values_and_duplicates() -> None:
    normalized_names = SubredditService.normalize_names(
        ["hungary", "r/Hungary", "", " /r/budapest ", "budapest/comments/example"]
    )

    assert normalized_names == ["hungary", "budapest"]
