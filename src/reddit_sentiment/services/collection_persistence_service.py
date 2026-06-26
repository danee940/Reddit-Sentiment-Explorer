from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
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
        self._subreddit_cache: dict[str, Subreddit] = {}

    async def persist_posts_and_comments(
        self,
        posts: list[CollectedPost],
        comments: list[CollectedComment],
        content_language: str,
    ) -> list[Document]:
        await self._warm_subreddit_cache(posts, comments)

        post_reddit_ids = [p.reddit_post_id for p in posts]
        existing_posts = await self._fetch_existing_posts(post_reddit_ids)

        stored_posts: dict[str, Post] = {}
        for post in posts:
            stored = existing_posts.get(post.reddit_post_id)
            if stored is None:
                stored = await self._insert_post(post)
            stored_posts[post.reddit_post_id] = stored

        cross_batch_post_ids = {
            c.reddit_post_id for c in comments if c.reddit_post_id not in stored_posts
        }
        if cross_batch_post_ids:
            cross_batch_posts = await self._fetch_existing_posts(list(cross_batch_post_ids))
            stored_posts.update(cross_batch_posts)

        comment_reddit_ids = [c.reddit_comment_id for c in comments]
        existing_comments = await self._fetch_existing_comments(comment_reddit_ids)

        stored_comments: dict[str, Comment] = {}
        for comment in comments:
            stored_comment = existing_comments.get(comment.reddit_comment_id)
            if stored_comment is None:
                parent_post = stored_posts.get(comment.reddit_post_id)
                stored_comment = await self._insert_comment(comment, parent_post)
            stored_comments[comment.reddit_comment_id] = stored_comment

        candidate_post_source_ids = [p.id for p in stored_posts.values()]
        candidate_comment_source_ids = [c.id for c in stored_comments.values()]
        existing_documents = await self._fetch_existing_documents(
            candidate_post_source_ids, candidate_comment_source_ids
        )

        documents: list[Document] = []

        for post in posts:
            stored_post = stored_posts[post.reddit_post_id]
            full_text = " ".join(part for part in [post.title, post.body] if part).strip()
            title_matches = self.search_service.match_text(post.title, "title")[0]
            body_matches = self.search_service.match_text(post.body, "body")[0]
            if not title_matches and not body_matches:
                continue
            doc = await self._get_or_create_document_from_cache(
                existing_documents=existing_documents,
                full_text=full_text,
                content_language=content_language,
                source_type=DocumentSourceType.post,
                source_id=stored_post.id,
                subreddit_id=self._subreddit_cache[post.subreddit].id,
                created_utc=post.created_utc,
                score=post.score,
                permalink=post.permalink,
            )
            if doc is not None:
                documents.append(doc)

        for comment in comments:
            stored_comment = stored_comments[comment.reddit_comment_id]
            if not self.search_service.match_text(comment.body, "comment")[0]:
                continue
            doc = await self._get_or_create_document_from_cache(
                existing_documents=existing_documents,
                full_text=comment.body,
                content_language=content_language,
                source_type=DocumentSourceType.comment,
                source_id=stored_comment.id,
                subreddit_id=self._subreddit_cache[comment.subreddit].id,
                created_utc=comment.created_utc,
                score=comment.score,
                permalink=comment.permalink,
            )
            if doc is not None:
                documents.append(doc)

        return documents

    async def _warm_subreddit_cache(
        self,
        posts: list[CollectedPost],
        comments: list[CollectedComment],
    ) -> None:
        names = {p.subreddit for p in posts} | {c.subreddit for c in comments}
        uncached = names - self._subreddit_cache.keys()
        if uncached:
            rows = (
                await self.session.scalars(
                    select(Subreddit).where(Subreddit.name.in_(uncached))
                )
            ).all()
            for row in rows:
                self._subreddit_cache[row.name] = row
            for name in uncached - {row.name for row in rows}:
                new_sub = Subreddit(
                    name=name,
                    is_enabled=True,
                    is_core=name in self.default_subreddits,
                )
                self.session.add(new_sub)
                await self.session.flush()
                self._subreddit_cache[name] = new_sub

    async def _fetch_existing_posts(self, reddit_ids: list[str]) -> dict[str, Post]:
        if not reddit_ids:
            return {}
        rows = (
            await self.session.scalars(
                select(Post).where(Post.reddit_post_id.in_(reddit_ids))
            )
        ).all()
        return {row.reddit_post_id: row for row in rows}

    async def _fetch_existing_comments(self, reddit_ids: list[str]) -> dict[str, Comment]:
        if not reddit_ids:
            return {}
        rows = (
            await self.session.scalars(
                select(Comment).where(Comment.reddit_comment_id.in_(reddit_ids))
            )
        ).all()
        return {row.reddit_comment_id: row for row in rows}

    async def _fetch_existing_documents(
        self,
        post_source_ids: list[str],
        comment_source_ids: list[str],
    ) -> dict[tuple[str, str], Document]:
        if not post_source_ids and not comment_source_ids:
            return {}
        conditions = []
        if post_source_ids:
            conditions.append(
                and_(
                    Document.source_type == DocumentSourceType.post,
                    Document.source_id.in_(post_source_ids),
                )
            )
        if comment_source_ids:
            conditions.append(
                and_(
                    Document.source_type == DocumentSourceType.comment,
                    Document.source_id.in_(comment_source_ids),
                )
            )
        rows = (
            await self.session.scalars(
                select(Document).where(or_(*conditions))
            )
        ).all()
        return {(row.source_type, row.source_id): row for row in rows}

    async def _insert_post(self, post: CollectedPost) -> Post:
        subreddit = self._subreddit_cache.get(post.subreddit)
        if subreddit is None:
            subreddit = await self._get_or_create_subreddit(post.subreddit)
        nested = await self.session.begin_nested()
        try:
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
        except IntegrityError:
            await nested.rollback()
            result = await self.session.scalar(
                select(Post).where(Post.reddit_post_id == post.reddit_post_id)
            )
            if result is None:
                raise
            return result
        else:
            await nested.commit()
        return stored_post

    async def _insert_comment(
        self, comment: CollectedComment, parent_post: Post | None
    ) -> Comment:
        nested = await self.session.begin_nested()
        try:
            stored_comment = Comment(
                reddit_comment_id=comment.reddit_comment_id,
                post_id=parent_post.id if parent_post else None,
                subreddit_id=self._subreddit_cache[comment.subreddit].id,
                body=comment.body,
                author_name=comment.author_name,
                score=comment.score,
                created_utc=comment.created_utc,
                permalink=comment.permalink,
                raw_payload=comment.raw_payload,
            )
            self.session.add(stored_comment)
            await self.session.flush()
        except IntegrityError:
            await nested.rollback()
            result = await self.session.scalar(
                select(Comment).where(Comment.reddit_comment_id == comment.reddit_comment_id)
            )
            if result is None:
                raise
            return result
        else:
            await nested.commit()
        return stored_comment

    async def _get_or_create_document_from_cache(
        self,
        existing_documents: dict[tuple[str, str], Document],
        full_text: str,
        content_language: str,
        source_type: DocumentSourceType,
        source_id: str,
        subreddit_id: str,
        created_utc,
        score: int,
        permalink: str,
    ) -> Document | None:
        cached = existing_documents.get((source_type, source_id))
        if cached is not None:
            return cached
        matches_language, lang, confidence = self.language_service.matches_language(
            full_text,
            content_language,
        )
        if not matches_language:
            return None
        document = Document(
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
        self.session.add(document)
        await self.session.flush()
        existing_documents[(source_type, source_id)] = document
        return document

    async def _get_or_create_subreddit(self, name: str) -> Subreddit:
        cached = self._subreddit_cache.get(name)
        if cached is not None:
            return cached
        subreddit = await self.session.scalar(select(Subreddit).where(Subreddit.name == name))
        if subreddit is None:
            subreddit = Subreddit(
                name=name,
                is_enabled=True,
                is_core=name in self.default_subreddits,
            )
            self.session.add(subreddit)
            await self.session.flush()
        self._subreddit_cache[name] = subreddit
        return subreddit
