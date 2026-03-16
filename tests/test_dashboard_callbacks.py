from types import SimpleNamespace

from reddit_sentiment.dashboard.callbacks import query as query_callbacks


def test_create_query_sends_content_language_separately_from_ui_language(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    def fake_api_request(method: str, path: str, payload: dict[str, object]) -> dict[str, object]:
        captured_payload.update({"method": method, "path": path, **payload})
        return {
            "query_id": "query-1",
            "query_run_id": "run-1",
            "status": "pending",
            "is_cached": False,
        }

    monkeypatch.setattr(query_callbacks, "api_request", fake_api_request)
    monkeypatch.setattr(
        query_callbacks,
        "settings",
        SimpleNamespace(default_subreddits=["hungary"]),
    )

    store_data, message, message_class, poll_disabled = query_callbacks.create_query(
        1,
        None,
        "en",
        "borscht",
        ["AskARussian"],
        "ru",
    )

    assert captured_payload == {
        "method": "POST",
        "path": "/queries",
        "term": "borscht",
        "subreddits": ["AskARussian"],
        "content_language": "ru",
    }
    assert store_data is not None
    assert store_data["content_language"] == "ru"
    assert message == "Query started: run-1"
    assert poll_disabled is False
    assert message_class == "mt-4 text-sm font-medium text-gray-600"
