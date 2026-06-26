from __future__ import annotations

import asyncio

import httpx

from reddit_sentiment.services.subreddit_service import SubredditService

# ---------------------------------------------------------------------------
# normalize_name edge cases
# ---------------------------------------------------------------------------


def test_normalize_name_returns_none_for_none_input() -> None:
    assert SubredditService.normalize_name(None) is None


def test_normalize_name_returns_none_for_empty_string() -> None:
    assert SubredditService.normalize_name("") is None


def test_normalize_name_handles_http_prefix() -> None:
    assert SubredditService.normalize_name("http://reddit.com/r/linux") == "linux"


def test_normalize_name_handles_deep_path() -> None:
    assert SubredditService.normalize_name("r/linux/comments/abc") == "linux"


def test_normalize_name_bare_name() -> None:
    assert SubredditService.normalize_name("linux") == "linux"


# ---------------------------------------------------------------------------
# validate_subreddits — using MockTransport
# ---------------------------------------------------------------------------


def _make_client_factory(responses: dict[str, int]):
    def route(request: httpx.Request) -> httpx.Response:
        for path_fragment, status in responses.items():
            if path_fragment in request.url.path:
                return httpx.Response(status)
        return httpx.Response(404)

    def factory(**kwargs) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(route), **kwargs)

    return factory


def test_validate_subreddits_returns_exists_true_for_200() -> None:
    factory = _make_client_factory({"/r/linux/": 200})
    service = SubredditService(client_factory=factory)

    results = asyncio.run(service.validate_subreddits(["linux"]))

    assert results == [{"name": "linux", "exists": True}]


def test_validate_subreddits_returns_exists_true_for_403() -> None:
    factory = _make_client_factory({"/r/private/": 403})
    service = SubredditService(client_factory=factory)

    results = asyncio.run(service.validate_subreddits(["private"]))

    assert results == [{"name": "private", "exists": True}]


def test_validate_subreddits_returns_exists_false_for_404() -> None:
    factory = _make_client_factory({"/r/doesnotexist/": 404})
    service = SubredditService(client_factory=factory)

    results = asyncio.run(service.validate_subreddits(["doesnotexist"]))

    assert results == [{"name": "doesnotexist", "exists": False}]


def test_validate_subreddits_returns_exists_none_for_unexpected_status() -> None:
    factory = _make_client_factory({"/r/broken/": 500})
    service = SubredditService(client_factory=factory)

    results = asyncio.run(service.validate_subreddits(["broken"]))

    assert results == [{"name": "broken", "exists": None}]


def test_validate_subreddits_returns_exists_none_on_http_error() -> None:
    def error_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    def factory(**kwargs) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(error_transport), **kwargs)

    service = SubredditService(client_factory=factory)

    results = asyncio.run(service.validate_subreddits(["linux"]))

    assert results == [{"name": "linux", "exists": None}]


def test_validate_subreddits_empty_list_returns_empty() -> None:
    service = SubredditService()

    results = asyncio.run(service.validate_subreddits([]))

    assert results == []


def test_validate_subreddits_deduplicates_names() -> None:
    factory = _make_client_factory({"/r/linux/": 200})
    service = SubredditService(client_factory=factory)

    results = asyncio.run(service.validate_subreddits(["linux", "r/linux", "Linux"]))

    assert len(results) == 1
    assert results[0]["name"] == "linux"
