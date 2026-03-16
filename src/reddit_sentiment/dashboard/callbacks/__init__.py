from __future__ import annotations

from dash import Dash

from reddit_sentiment.dashboard.callbacks import (
    clientside,
    documents,
    query,
    results,
    theme_language,
)
from reddit_sentiment.dashboard.constants import settings
from reddit_sentiment.dashboard.helpers import api_request


def create_query(
    n_clicks,
    language: str | None,
    term: str | None,
    subreddit_names: list[str] | None,
    content_language: str | None,
):
    original_api_request = query.api_request
    original_settings = query.settings
    query.api_request = api_request
    query.settings = settings
    try:
        return query.create_query(
            n_clicks,
            None,
            language,
            term,
            subreddit_names,
            content_language,
        )
    finally:
        query.api_request = original_api_request
        query.settings = original_settings


def register_callbacks(app: Dash) -> None:
    clientside.register(app)
    theme_language.register(app)
    query.register(app)
    results.register(app)
    documents.register(app)
