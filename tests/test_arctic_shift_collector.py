import asyncio

import httpx
import pytest

from reddit_sentiment.collectors.arctic_shift.client import ArcticShiftCollector
from reddit_sentiment.core.config import Settings


def _make_collector(transport: httpx.MockTransport, max_retries: int = 2) -> ArcticShiftCollector:
    settings = Settings(
        arctic_shift_max_retries=max_retries,
        arctic_shift_retry_backoff=0.0,
    )

    def client_factory(**kwargs: object) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport, base_url="https://example.test")

    return ArcticShiftCollector(settings=settings, client_factory=client_factory)


async def test_request_retries_transient_status_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(422, json={"error": "transient"})
        return httpx.Response(200, json={"data": [{"id": "post1", "subreddit": "kde"}]})

    collector = _make_collector(httpx.MockTransport(handler))
    async with collector.client_factory() as client:
        semaphore = asyncio.Semaphore(1)
        payload = await collector._request_posts(
            client=client,
            subreddit_name="kde",
            term="windows",
            limit=100,
            semaphore=semaphore,
        )

    assert attempts["count"] == 3
    assert ArcticShiftCollector._extract_items(payload) == [{"id": "post1", "subreddit": "kde"}]


async def test_request_skips_after_exhausting_retries() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(422, json={"error": "always transient"})

    collector = _make_collector(httpx.MockTransport(handler), max_retries=2)
    async with collector.client_factory() as client:
        semaphore = asyncio.Semaphore(1)
        payload = await collector._request_posts(
            client=client,
            subreddit_name="kde",
            term="windows",
            limit=100,
            semaphore=semaphore,
        )

    assert attempts["count"] == 3
    assert payload == []


async def test_request_does_not_retry_non_transient_status() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(400, json={"error": "'limit' must be between 1 and 100"})

    collector = _make_collector(httpx.MockTransport(handler), max_retries=2)
    async with collector.client_factory() as client:
        semaphore = asyncio.Semaphore(1)
        with pytest.raises(httpx.HTTPStatusError):
            await collector._request_posts(
                client=client,
                subreddit_name="kde",
                term="windows",
                limit=101,
                semaphore=semaphore,
            )

    assert attempts["count"] == 1


def test_extract_items_supports_data_list_payload() -> None:
    payload = {"data": [{"id": "abc"}, {"id": "def"}]}
    items = ArcticShiftCollector._extract_items(payload)
    assert items == [{"id": "abc"}, {"id": "def"}]


def test_normalize_post_maps_expected_fields() -> None:
    post = ArcticShiftCollector._normalize_post(
        {
            "id": "post123",
            "subreddit": "hungary",
            "title": "Big Mac megint dragabb lett",
            "selftext": "Szerintem mar nem eri meg.",
            "author": "user_1",
            "score": 12,
            "created_utc": 1710000000,
            "permalink": "/r/hungary/comments/post123/example/",
        }
    )
    assert post is not None
    assert post.reddit_post_id == "post123"
    assert post.subreddit == "hungary"
    assert post.author_name == "user_1"
    assert post.permalink == "https://reddit.com/r/hungary/comments/post123/example/"


def test_normalize_comment_uses_parent_post_id() -> None:
    comment = ArcticShiftCollector._normalize_comment(
        {
            "id": "comment123",
            "subreddit": "hungary",
            "body": "A Big Mac szerintem mar nem jo.",
            "author": "user_2",
            "score": 4,
            "created_utc": "1710000123",
            "permalink": "/r/hungary/comments/post123/example/comment123/",
        },
        post_id="post123",
        subreddit="hungary",
    )
    assert comment is not None
    assert comment.reddit_post_id == "post123"
    assert comment.reddit_comment_id == "comment123"
    assert comment.subreddit == "hungary"


def test_normalize_permalink_builds_fallback_permalink() -> None:
    permalink = ArcticShiftCollector._normalize_permalink(None, "post999", "askhungary")
    assert permalink == "https://reddit.com/r/askhungary/comments/post999"
