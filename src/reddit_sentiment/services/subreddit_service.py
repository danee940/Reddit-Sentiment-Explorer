from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx


class SubredditService:
    def __init__(
        self,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
    ) -> None:
        self.client_factory = client_factory or httpx.AsyncClient

    async def validate_subreddits(self, names: list[str]) -> list[dict[str, bool | None | str]]:
        normalized_names = self.normalize_names(names)
        if not normalized_names:
            return []

        async with self.client_factory(
            base_url="https://www.reddit.com",
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": "RedditSentimentExplorer/1.0"},
        ) as client:
            results = await asyncio.gather(
                *(self._validate_subreddit(client, name) for name in normalized_names)
            )
        return results

    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower().strip("/")
        normalized = normalized.removeprefix("https://")
        normalized = normalized.removeprefix("http://")
        normalized = normalized.removeprefix("www.")
        if normalized.startswith("r/"):
            normalized = normalized[2:]
        if normalized.startswith("reddit.com/r/"):
            normalized = normalized[len("reddit.com/r/") :]
        if "/" in normalized:
            normalized = normalized.split("/", maxsplit=1)[0]
        return normalized or None

    @classmethod
    def normalize_names(cls, values: list[str]) -> list[str]:
        normalized_names: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = cls.normalize_name(value)
            if normalized is None or normalized in seen:
                continue
            normalized_names.append(normalized)
            seen.add(normalized)
        return normalized_names

    async def _validate_subreddit(
        self,
        client: httpx.AsyncClient,
        name: str,
    ) -> dict[str, bool | None | str]:
        try:
            response = await client.get(f"/r/{name}/about.json")
        except httpx.HTTPError:
            return {"name": name, "exists": None}

        if response.status_code in {200, 403}:
            return {"name": name, "exists": True}
        if response.status_code == 404:
            return {"name": name, "exists": False}
        return {"name": name, "exists": None}
