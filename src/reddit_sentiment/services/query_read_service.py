from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.enums import SentimentLabel
from reddit_sentiment.db.models import (
    Document,
    Query,
    QueryDocumentMatch,
    QueryRun,
    SentimentResult,
    Subreddit,
)


@dataclass(slots=True)
class QueryRunDocument:
    document_id: str
    source_type: str
    subreddit: str
    created_utc: datetime
    score: int
    snippet: str
    content: str
    sentiment_label: SentimentLabel | None
    sentiment_score: int | None
    sentiment_confidence: float | None = None
    sentiment_rationale: str | None = None
    sentiment_evidence_phrases: list[str] = field(default_factory=list)
    permalink: str | None = None


class QueryReadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_run_for_provider(
        self,
        query_id: str,
        sentiment_provider_name: str,
        sentiment_provider_version: str,
    ) -> QueryRun | None:
        stmt = (
            select(QueryRun)
            .where(QueryRun.query_id == query_id)
            .where(QueryRun.sentiment_provider_name == sentiment_provider_name)
            .where(QueryRun.sentiment_provider_version == sentiment_provider_version)
            .order_by(desc(QueryRun.started_at))
        )
        return cast(QueryRun | None, await self.session.scalar(stmt))

    async def get_run(self, run_id: str) -> QueryRun | None:
        return await self.session.get(QueryRun, run_id)

    async def get_query(self, query_id: str) -> Query | None:
        return await self.session.get(Query, query_id)

    async def get_run_documents(self, run_id: str) -> list[QueryRunDocument]:
        stmt = (
            select(Document, SentimentResult, Subreddit)
            .join(QueryDocumentMatch, QueryDocumentMatch.document_id == Document.id)
            .join(Subreddit, Subreddit.id == Document.subreddit_id)
            .outerjoin(
                SentimentResult,
                (SentimentResult.document_id == Document.id)
                & (SentimentResult.query_run_id == run_id),
            )
            .where(QueryDocumentMatch.query_run_id == run_id)
            .order_by(Document.created_utc.desc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            QueryRunDocument(
                document_id=document.id,
                source_type=document.source_type.value,
                subreddit=subreddit.name,
                created_utc=document.created_utc,
                score=document.score,
                snippet=document.full_text[:280],
                content=document.full_text,
                sentiment_label=sentiment.label if sentiment else None,
                sentiment_score=sentiment.score_value if sentiment else None,
                sentiment_confidence=sentiment.confidence if sentiment else None,
                sentiment_rationale=sentiment.rationale if sentiment else None,
                sentiment_evidence_phrases=sentiment.evidence_phrases if sentiment else [],
                permalink=document.permalink,
            )
            for document, sentiment, subreddit in rows
        ]
