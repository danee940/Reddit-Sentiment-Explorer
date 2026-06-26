from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.composition import (
    QueryPipelineServices,
    create_query_pipeline_services,
)
from reddit_sentiment.db.models import Document, QueryRun

logger = logging.getLogger(__name__)


async def run_query_pipeline(
    session: AsyncSession,
    query_run: QueryRun,
    term: str,
    subreddit_names: list[str],
    services: QueryPipelineServices | None = None,
) -> None:
    run_id = query_run.id
    pipeline_services = services or create_query_pipeline_services(session, term, query_run)
    collection_service = pipeline_services.collection_persistence_service
    match_service = pipeline_services.document_match_service

    await pipeline_services.query_service.mark_running(query_run)
    await session.commit()

    try:
        logger.info(
            "query_pipeline_started run_id=%s term=%s subreddit_count=%s language=%s",
            run_id,
            term,
            len(subreddit_names),
            query_run.language_filter,
        )
        posts, comments = await pipeline_services.collector.collect(
            term=term,
            subreddit_names=subreddit_names,
        )

        persisted_documents: list[Document] = []
        for post in posts:
            doc = await collection_service.persist_post(
                post,
                query_run.language_filter,
            )
            if doc is not None:
                persisted_documents.append(doc)

        for comment in comments:
            doc = await collection_service.persist_comment(
                comment,
                query_run.language_filter,
            )
            if doc is not None:
                persisted_documents.append(doc)

        matched_documents: list[Document] = []
        for document in persisted_documents:
            if await match_service.match_and_persist(
                query_run,
                document,
                pipeline_services.search_service,
            ):
                matched_documents.append(document)

        await pipeline_services.sentiment_service.classify_documents(
            query_run, matched_documents
        )

        await pipeline_services.aggregation_service.build(query_run.id)
        await pipeline_services.query_service.mark_completed(query_run)
        await session.commit()
        logger.info(
            "query_pipeline_completed run_id=%s persisted_documents=%s matched_documents=%s",
            run_id,
            len(persisted_documents),
            len(matched_documents),
        )
    except Exception as exc:
        await session.rollback()
        failed_run = await pipeline_services.query_service.get_run(run_id)
        if failed_run is not None:
            await pipeline_services.query_service.mark_failed(failed_run, str(exc))
            await session.commit()
        logger.exception("query_pipeline_failed run_id=%s error=%s", run_id, exc)
