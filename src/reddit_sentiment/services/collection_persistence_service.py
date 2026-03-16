from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_sentiment.collectors.arctic_shift.client import (
    CollectedComment,
    CollectedPost,
)
from reddit_sentiment.core.enums import DocumentSourceType
from reddit_sentiment.db.models import Comment, Document, Post, Subreddit
from reddit_sentiment.services.language_service import LanguageService
from reddit_sentiment.services.search_service import SearchService


class CollectionPersistenceService:
    def __init__(
        self,
        session: AsyncSession,
        language_service: LanguageService,
        search_service: SearchService,
        default_subreddits: set[str],
    ) -> None:
        self.session = session
        self.language_service = language_service
        self.search_service = search_service
        self.default_subreddits = default_subreddits

    async def persist_post(
        self,
        post: CollectedPost,
        content_language: str,
    ) -> Document | None:
        subreddit = await self._get_or_create_subreddit(post.subreddit)
        stored_post = await self.session.scalar(
            select(Post).where(Post.reddit_post_id == post.reddit_post_id)
        )
        if stored_post is None:
            stored_post = Post(
                reddit_post_id=post.reddit_post_id,
                subreddit_id=subreddit.id,
                title=post.title,
                body=post.body,
                author_name=post.author_name,
                score=post.score,
                created_utc=post.created_utc,
                permalink=post.permalink,
                raw_payload=post.raw_payload,
            )
            self.session.add(stored_post)
            await self.session.flush()

        full_text = " ".join(part for part in [post.title, post.body] if part).strip()
        title_matches = self.search_service.match_text(post.title, "title")[0]
        body_matches = self.search_service.match_text(post.body, "body")[0]
        if not title_matches and not body_matches:
            return None
        return await self._check_language_and_persist_document(
            full_text=full_text,
            content_language=content_language,
            source_type=DocumentSourceType.post,
            source_id=stored_post.id,
            subreddit_id=subreddit.id,
            created_utc=post.created_utc,
            score=post.score,
            permalink=post.permalink,
        )

    async def persist_comment(
        self,
        comment: CollectedComment,
        content_language: str,
    ) -> Document | None:
        subreddit = await self._get_or_create_subreddit(comment.subreddit)
        stored_post = await self.session.scalar(
            select(Post).where(Post.reddit_post_id == comment.reddit_post_id)
        )
        stored_comment = await self.session.scalar(
            select(Comment).where(Comment.reddit_comment_id == comment.reddit_comment_id)
        )
        if stored_comment is None:
            stored_comment = Comment(
                reddit_comment_id=comment.reddit_comment_id,
                post_id=stored_post.id if stored_post else None,
                subreddit_id=subreddit.id,
                body=comment.body,
                author_name=comment.author_name,
                score=comment.score,
                created_utc=comment.created_utc,
                permalink=comment.permalink,
                raw_payload=comment.raw_payload,
            )
            self.session.add(stored_comment)
            await self.session.flush()

        if not self.search_service.match_text(comment.body, "comment")[0]:
            return None
        return await self._check_language_and_persist_document(
            full_text=comment.body,
            content_language=content_language,
            source_type=DocumentSourceType.comment,
            source_id=stored_comment.id,
            subreddit_id=subreddit.id,
            created_utc=comment.created_utc,
            score=comment.score,
            permalink=comment.permalink,
        )

    async def _get_or_create_subreddit(self, name: str) -> Subreddit:
        subreddit = await self.session.scalar(select(Subreddit).where(Subreddit.name == name))
        if subreddit is not None:
            return subreddit
        subreddit = Subreddit(
            name=name,
            is_enabled=True,
            is_core=name in self.default_subreddits,
        )
        self.session.add(subreddit)
        await self.session.flush()
        return subreddit

    async def _check_language_and_persist_document(
        self,
        full_text: str,
        content_language: str,
        source_type: DocumentSourceType,
        source_id: str,
        subreddit_id: str,
        created_utc,
        score: int,
        permalink: str,
    ) -> Document | None:
        matches_language, lang, confidence = self.language_service.matches_language(
            full_text,
            content_language,
        )
        if not matches_language:
            return None
        return await self._get_or_create_document(
            source_type=source_type,
            source_id=source_id,
            subreddit_id=subreddit_id,
            full_text=full_text,
            detected_language=lang,
            language_confidence=confidence,
            created_utc=created_utc,
            score=score,
            permalink=permalink,
        )

    async def _get_or_create_document(
        self,
        source_type: DocumentSourceType,
        source_id: str,
        subreddit_id: str,
        full_text: str,
        detected_language: str | None,
        language_confidence: float | None,
        created_utc,
        score: int,
        permalink: str,
    ) -> Document:
        document = await self.session.scalar(
            select(Document)
            .where(Document.source_type == source_type)
            .where(Document.source_id == source_id)
        )
        if document is not None:
            return document
        document = Document(
            source_type=source_type,
            source_id=source_id,
            subreddit_id=subreddit_id,
            full_text=full_text,
            detected_language=detected_language,
            language_confidence=language_confidence,
            created_utc=created_utc,
            score=score,
            permalink=permalink,
        )
        self.session.add(document)
        await self.session.flush()
        return document
