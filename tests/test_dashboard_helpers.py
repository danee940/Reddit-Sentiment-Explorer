from __future__ import annotations

from reddit_sentiment.dashboard.helpers import parse_subreddit_input


def test_parse_subreddit_input_returns_empty_for_none() -> None:
    assert parse_subreddit_input(None) == []


def test_parse_subreddit_input_returns_empty_for_blank() -> None:
    assert parse_subreddit_input("") == []
    assert parse_subreddit_input("   ") == []


def test_parse_subreddit_input_single_name() -> None:
    assert parse_subreddit_input("hungary") == ["hungary"]


def test_parse_subreddit_input_comma_separated() -> None:
    assert parse_subreddit_input("hungary, budapest") == ["hungary", "budapest"]


def test_parse_subreddit_input_newline_separated() -> None:
    assert parse_subreddit_input("hungary\nbudapest") == ["hungary", "budapest"]


def test_parse_subreddit_input_newline_and_comma_mixed() -> None:
    assert parse_subreddit_input("hungary\nbudapest, askhungary") == [
        "hungary",
        "budapest",
        "askhungary",
    ]


def test_parse_subreddit_input_strips_r_prefix() -> None:
    assert parse_subreddit_input("r/hungary") == ["hungary"]


def test_parse_subreddit_input_deduplicates() -> None:
    assert parse_subreddit_input("hungary, Hungary, hungary") == ["hungary"]


def test_parse_subreddit_input_normalizes_full_url() -> None:
    assert parse_subreddit_input("https://www.reddit.com/r/hungary/") == ["hungary"]


def test_parse_subreddit_input_lowercases_names() -> None:
    assert parse_subreddit_input("AskHungary, Budapest") == ["askhungary", "budapest"]


def test_parse_subreddit_input_skips_empty_segments() -> None:
    assert parse_subreddit_input("hungary,,budapest") == ["hungary", "budapest"]
