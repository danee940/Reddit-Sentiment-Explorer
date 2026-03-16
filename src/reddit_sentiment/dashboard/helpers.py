from __future__ import annotations

import json
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from reddit_sentiment.dashboard.constants import SENTIMENT_ORDER, settings
from reddit_sentiment.dashboard.translations import t, translate_sentiment_label
from reddit_sentiment.services.subreddit_service import SubredditService


def api_request(method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url=f"{settings.api_base_url}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        if detail:
            try:
                parsed = json.loads(detail)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict) and parsed.get("detail"):
                return {"error": str(parsed["detail"])}
        return {"error": detail or str(exc)}
    except URLError as exc:
        return {"error": str(exc)}


def normalize_subreddit_name(value: str) -> str | None:
    return SubredditService.normalize_name(value)


def parse_subreddit_input(value: str | None) -> list[str]:
    if not value:
        return []
    subreddits: list[str] = []
    seen: set[str] = set()
    for raw_value in value.replace("\n", ",").split(","):
        normalized = normalize_subreddit_name(raw_value)
        if normalized is None or normalized in seen:
            continue
        subreddits.append(normalized)
        seen.add(normalized)
    return subreddits


def get_default_subreddit_text() -> str:
    return ", ".join(f"r/{name}" for name in settings.default_subreddits)


def sentiment_rank(label: str) -> int:
    try:
        return SENTIMENT_ORDER.index(label)
    except ValueError:
        return len(SENTIMENT_ORDER)


def sort_sentiment_distribution(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: sentiment_rank(str(item.get("label", ""))))


def normalize_timeline_items(items: list[dict], key: str) -> list[dict]:
    return sorted(items, key=lambda item: str(item.get(key, "")))


def format_document_timestamp(value: str | None, language: str | None) -> str:
    if not value:
        return t(language, "unknown_date")
    return value.replace("T", " ").replace("Z", " UTC")


def format_document_date_bucket(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value)
    if "T" in text:
        return text.split("T", maxsplit=1)[0]
    if " " in text:
        return text.split(" ", maxsplit=1)[0]
    return text


def prepare_document_items(items: list[dict], language: str | None) -> list[dict]:
    prepared_items = []
    for item in items:
        content = item.get("content") or item.get("snippet") or ""
        snippet_preview = content if len(content) <= 180 else f"{content[:177].rstrip()}..."
        prepared_items.append(
            {
                **item,
                "id": item.get("document_id"),
                "display_date": format_document_timestamp(item.get("created_utc"), language),
                "date_bucket": format_document_date_bucket(item.get("created_utc")),
                "snippet_preview": snippet_preview,
                "sentiment_text": translate_sentiment_label(item.get("sentiment_label"), language),
            }
        )
    return prepared_items


def serialize_document_table_rows(items: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for item in items:
        rows.append({key: _serialize_document_table_value(value) for key, value in item.items()})
    return rows


def _serialize_document_table_value(value):
    if isinstance(value, list):
        if all(not isinstance(item, (dict, list)) for item in value):
            return ", ".join(str(item) for item in value)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return value
