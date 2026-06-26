from __future__ import annotations

from reddit_sentiment.dashboard.translations import (
    build_history_status,
    build_status_message,
    format_history_time,
    format_matches_summary,
    format_selected_subreddit_count,
    translate_source_label,
    translate_status_label,
)


def test_translate_status_label_completed() -> None:
    result = translate_status_label("completed", "en")
    assert result


def test_translate_status_label_failed() -> None:
    result = translate_status_label("failed", "en")
    assert result


def test_translate_status_label_pending() -> None:
    result = translate_status_label("pending", "en")
    assert result


def test_translate_status_label_running() -> None:
    result = translate_status_label("running", "en")
    assert result


def test_translate_status_label_unknown_non_none_titlecases() -> None:
    result = translate_status_label("some_custom_state", "en")
    assert result == "Some Custom State"


def test_translate_status_label_none_returns_stored() -> None:
    result = translate_status_label(None, "en")
    assert result


def test_translate_source_label_post() -> None:
    result = translate_source_label("post", "en")
    assert result


def test_translate_source_label_comment() -> None:
    result = translate_source_label("comment", "en")
    assert result


def test_translate_source_label_none_fallback() -> None:
    result = translate_source_label(None, "en")
    assert result


def test_format_selected_subreddit_count_english_singular() -> None:
    result = format_selected_subreddit_count("en", 1)
    assert "1" in result
    assert "selected" in result
    assert "subreddits" not in result


def test_format_selected_subreddit_count_english_plural() -> None:
    result = format_selected_subreddit_count("en", 3)
    assert "3" in result
    assert "subreddits" in result


def test_format_selected_subreddit_count_hungarian() -> None:
    result = format_selected_subreddit_count("hu", 2)
    assert "2" in result
    assert "subreddit" in result


def test_format_matches_summary_english_plural() -> None:
    result = format_matches_summary("en", 5, 2)
    assert "5" in result
    assert "matches" in result


def test_format_matches_summary_english_singular() -> None:
    result = format_matches_summary("en", 1, 1)
    assert "1 match" in result
    assert "matches" not in result


def test_format_matches_summary_hungarian() -> None:
    result = format_matches_summary("hu", 3, 2)
    assert "3" in result
    assert "2" in result


def test_format_history_time_none_returns_fallback() -> None:
    result = format_history_time(None, "en")
    assert result


def test_format_history_time_invalid_date_returns_fallback() -> None:
    result = format_history_time("not-a-valid-date", "en")
    assert result


def test_format_history_time_valid_iso_formats_correctly() -> None:
    result = format_history_time("2024-06-01T12:00:00Z", "en")
    assert "2024-06-01" in result
    assert "UTC" in result


def test_build_history_status_delegates_to_translate() -> None:
    result = build_history_status("completed", "en")
    assert result


def test_build_status_message_none_store_returns_empty() -> None:
    result = build_status_message(None, "en")
    assert result == ""


def test_build_status_message_completed() -> None:
    result = build_status_message({"status": "completed"}, "en")
    assert result


def test_build_status_message_failed_includes_error() -> None:
    result = build_status_message({"status": "failed", "error_message": "timeout occurred"}, "en")
    assert "timeout occurred" in result


def test_build_status_message_failed_no_error_message() -> None:
    result = build_status_message({"status": "failed"}, "en")
    assert result


def test_build_status_message_other_status_shows_status() -> None:
    result = build_status_message({"status": "running"}, "en")
    assert result
