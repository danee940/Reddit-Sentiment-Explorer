from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.core.enums import DocumentSourceType
from reddit_sentiment.db.models import Document, QueryDocumentMatch, QueryRun
from reddit_sentiment.services.search_service import SearchService


class DocumentMatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def match_and_persist_batch(
        self,
        query_run: QueryRun,
        documents: list[Document],
        search_service: SearchService,
    ) -> list[Document]:
        document_ids = [d.id for d in documents]
        existing_document_ids: set[str] = set()
        if document_ids:
            existing_rows = await self.session.scalars(
                select(QueryDocumentMatch.document_id)
                .where(QueryDocumentMatch.query_run_id == query_run.id)
                .where(QueryDocumentMatch.document_id.in_(document_ids))
            )
            existing_document_ids = set(existing_rows.all())

        matched: list[Document] = []
        for document in documents:
            if document.id in existing_document_ids:
                matched.append(document)
                continue
            source_kind = (
                "comment" if document.source_type == DocumentSourceType.comment else "body"
            )
            is_matched, match_type, matched_terms, relevance_score = search_service.match_text(
                document.full_text,
                source_kind,
            )
            if not is_matched or match_type is None:
                continue
            match = QueryDocumentMatch(
                query_run_id=query_run.id,
                document_id=document.id,
                match_type=match_type.value,
                matched_terms=matched_terms,
                relevance_score=relevance_score,
            )
            self.session.add(match)
            matched.append(document)
        await self.session.flush()
        return matched
