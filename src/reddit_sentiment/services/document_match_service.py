from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.enums import DocumentSourceType
from reddit_sentiment.db.models import Document, QueryDocumentMatch, QueryRun
from reddit_sentiment.services.search_service import SearchService


class DocumentMatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def match_and_persist(
        self,
        query_run: QueryRun,
        document: Document,
        search_service: SearchService,
    ) -> bool:
        source_kind = (
            "comment" if document.source_type == DocumentSourceType.comment else "body"
        )
        matched, match_type, matched_terms, relevance_score = search_service.match_text(
            document.full_text,
            source_kind,
        )
        if not matched or match_type is None:
            return False
        exists = await self.session.scalar(
            select(QueryDocumentMatch)
            .where(QueryDocumentMatch.query_run_id == query_run.id)
            .where(QueryDocumentMatch.document_id == document.id)
        )
        if exists is not None:
            return True
        match = QueryDocumentMatch(
            query_run_id=query_run.id,
            document_id=document.id,
            match_type=match_type.value,
            matched_terms=matched_terms,
            relevance_score=relevance_score,
        )
        self.session.add(match)
        await self.session.flush()
        return True
