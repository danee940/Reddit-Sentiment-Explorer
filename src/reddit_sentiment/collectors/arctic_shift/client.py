from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

import httpx

from reddit_sentiment.core.config import Settings, get_settings


@dataclass(slots=True)
class CollectedPost:
    reddit_post_id: str
    subreddit: str
    title: str
    body: str
    author_name: str | None
    score: int
    created_utc: datetime
    permalink: str
    raw_payload: dict


@dataclass(slots=True)
class CollectedComment:
    reddit_comment_id: str
    reddit_post_id: str
    subreddit: str
    body: str
    author_name: str | None
    score: int
    created_utc: datetime
    permalink: str
    raw_payload: dict


class ArcticShiftCollector:
    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client_factory = client_factory or httpx.AsyncClient

    async def collect(
        self,
        term: str,
        subreddit_names: list[str],
        limit: int | None = None,
    ) -> tuple[list[CollectedPost], list[CollectedComment]]:
        request_limit = self.settings.arctic_shift_request_limit if limit is None else limit
        posts: list[CollectedPost] = []
        comments: list[CollectedComment] = []

        async with self.client_factory(
            base_url=self.settings.arctic_shift_base_url,
            timeout=60.0,
        ) as client:
            for subreddit_name in subreddit_names:
                post_payload = await self._request_posts(
                    client=client,
                    subreddit_name=subreddit_name,
                    term=term,
                    limit=request_limit,
                )
                for item in self._extract_items(post_payload):
                    post = self._normalize_post(item)
                    if post is None:
                        continue
                    posts.append(post)

                    comment_payload = await self._request_comments(
                        client=client,
                        post_id=post.reddit_post_id,
                        limit=self.settings.arctic_shift_comment_limit,
                    )
                    for comment_item in self._extract_items(comment_payload):
                        comment = self._normalize_comment(
                            comment_item,
                            post.reddit_post_id,
                            post.subreddit,
                        )
                        if comment is not None:
                            comments.append(comment)

        return posts, comments

    async def _request_posts(
        self,
        client: httpx.AsyncClient,
        subreddit_name: str,
        term: str,
        limit: int | Literal["auto"],
    ) -> dict | list:
        response = await client.get(
            "/posts/search",
            params={
                "subreddit": subreddit_name,
                "query": term,
                "limit": limit,
            },
        )
        response.raise_for_status()
        return cast(dict[str, Any] | list[Any], response.json())

    async def _request_comments(
        self,
        client: httpx.AsyncClient,
        post_id: str,
        limit: int | Literal["auto"],
    ) -> dict | list:
        response = await client.get(
            "/comments/search",
            params={
                "link_id": post_id,
                "limit": limit,
            },
        )
        response.raise_for_status()
        return cast(dict[str, Any] | list[Any], response.json())

    @staticmethod
    def _extract_items(payload: dict | list) -> list[dict]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return [item for item in data if isinstance(item, dict)]
            if isinstance(data, dict):
                nested = data.get("items")
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
        return []

    @staticmethod
    def _normalize_post(item: dict) -> CollectedPost | None:
        post_id = item.get("id")
        subreddit = item.get("subreddit")
        if not post_id or not subreddit:
            return None
        permalink = ArcticShiftCollector._normalize_permalink(
            item.get("permalink"),
            post_id,
            subreddit,
        )
        return CollectedPost(
            reddit_post_id=str(post_id),
            subreddit=str(subreddit),
            title=str(item.get("title") or ""),
            body=str(item.get("selftext") or ""),
            author_name=str(item["author"]) if item.get("author") is not None else None,
            score=int(item.get("score") or 0),
            created_utc=ArcticShiftCollector._normalize_created_utc(item.get("created_utc")),
            permalink=permalink,
            raw_payload=item,
        )

    @staticmethod
    def _normalize_comment(
        item: dict,
        post_id: str,
        subreddit: str,
    ) -> CollectedComment | None:
        comment_id = item.get("id")
        if not comment_id:
            return None
        permalink = ArcticShiftCollector._normalize_permalink(
            item.get("permalink"),
            post_id,
            subreddit,
        )
        return CollectedComment(
            reddit_comment_id=str(comment_id),
            reddit_post_id=post_id,
            subreddit=str(item.get("subreddit") or subreddit),
            body=str(item.get("body") or ""),
            author_name=str(item["author"]) if item.get("author") is not None else None,
            score=int(item.get("score") or 0),
            created_utc=ArcticShiftCollector._normalize_created_utc(item.get("created_utc")),
            permalink=permalink,
            raw_payload=item,
        )

    @staticmethod
    def _normalize_created_utc(value: int | float | str | None) -> datetime:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=UTC)
        if isinstance(value, str):
            if value.isdigit():
                return datetime.fromtimestamp(int(value), tz=UTC)
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.now(tz=UTC)

    @staticmethod
    def _normalize_permalink(permalink: str | None, object_id: str, subreddit: str) -> str:
        if permalink:
            if permalink.startswith("http://") or permalink.startswith("https://"):
                return permalink
            return f"https://reddit.com{permalink}"
        return f"https://reddit.com/r/{subreddit}/comments/{object_id}"
