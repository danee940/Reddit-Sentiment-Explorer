from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from reddit_sentiment.collectors.arctic_shift.client import CollectedComment, CollectedPost
from reddit_sentiment.core.enums import DocumentSourceType
from reddit_sentiment.db.models import Comment, Document, Post, Subreddit
from reddit_sentiment.services.collection_persistence_service import CollectionPersistenceService
from reddit_sentiment.services.document_match_service import DocumentMatchService
from reddit_sentiment.services.language_service import LanguageService
from reddit_sentiment.services.search_service import SearchService


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _make_post(reddit_post_id: str = "p1", subreddit: str = "hungary") -> CollectedPost:
    return CollectedPost(
        reddit_post_id=reddit_post_id,
        subreddit=subreddit,
        title="Tisza Peter campaign",
        body="Great speech",
        author_name="user1",
        score=10,
        created_utc=_utc_now(),
        permalink="https://reddit.com/r/hungary/p1",
        raw_payload={},
    )


def _make_comment(
    reddit_comment_id: str = "c1",
    reddit_post_id: str = "p1",
    subreddit: str = "hungary",
    body: str = "I support Tisza",
) -> CollectedComment:
    return CollectedComment(
        reddit_comment_id=reddit_comment_id,
        reddit_post_id=reddit_post_id,
        subreddit=subreddit,
        body=body,
        author_name="user2",
        score=5,
        created_utc=_utc_now(),
        permalink="https://reddit.com/r/hungary/c1",
        raw_payload={},
    )


class FakeSession:
    def __init__(self) -> None:
        self._added: list[Any] = []
        self._flushed = 0
        self._subreddits: dict[str, Subreddit] = {}
        self._posts: dict[str, Post] = {}
        self._comments: dict[str, Comment] = {}
        self._documents: list[Document] = []

    def add(self, obj: Any) -> None:
        self._added.append(obj)
        if isinstance(obj, Subreddit):
            obj.id = f"sub-{obj.name}"
            self._subreddits[obj.name] = obj
        elif isinstance(obj, Post):
            obj.id = f"post-{obj.reddit_post_id}"
            self._posts[obj.reddit_post_id] = obj
        elif isinstance(obj, Comment):
            obj.id = f"comment-{obj.reddit_comment_id}"
            self._comments[obj.reddit_comment_id] = obj
        elif isinstance(obj, Document):
            obj.id = f"doc-{obj.source_id}"
            self._documents.append(obj)

    async def flush(self) -> None:
        self._flushed += 1

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def __init__(self, items: list) -> None:
                self._items = items

            def all(self) -> list:
                return self._items

        return _Result([])

    async def scalar(self, stmt: Any) -> Any:
        return None

    async def begin_nested(self) -> Any:
        class _Nested:
            async def commit(self) -> None:
                pass

            async def rollback(self) -> None:
                pass

        return _Nested()


class BatchFakeSession(FakeSession):
    def __init__(
        self,
        existing_subreddits: list[Subreddit] | None = None,
        existing_posts: list[Post] | None = None,
        existing_comments: list[Comment] | None = None,
        existing_documents: list[Document] | None = None,
    ) -> None:
        super().__init__()
        self._existing_subreddits = existing_subreddits or []
        self._existing_posts = existing_posts or []
        self._existing_comments = existing_comments or []
        self._existing_documents = existing_documents or []
        self.scalar_calls = 0
        self.scalars_calls = 0

    async def scalars(self, stmt: Any) -> Any:
        self.scalars_calls += 1

        class _Result:
            def __init__(self, items: list) -> None:
                self._items = items

            def all(self) -> list:
                return self._items

        compiled = str(stmt)
        if "subreddits" in compiled:
            return _Result(self._existing_subreddits)
        if "posts" in compiled:
            return _Result(self._existing_posts)
        if "comments" in compiled:
            return _Result(self._existing_comments)
        if "documents" in compiled:
            return _Result(self._existing_documents)
        return _Result([])

    async def scalar(self, stmt: Any) -> Any:
        self.scalar_calls += 1
        return None


def _build_service(
    session: Any,
    term: str = "Tisza",
    default_subreddits: set[str] | None = None,
) -> CollectionPersistenceService:
    return CollectionPersistenceService(
        session=session,
        language_service=LanguageService(),
        search_service=SearchService(term),
        default_subreddits=default_subreddits or {"hungary"},
    )


def test_persist_posts_and_comments_returns_matched_documents() -> None:
    session = BatchFakeSession()
    service = _build_service(session, term="Tisza")
    post = _make_post()
    comment = _make_comment()

    docs = asyncio.run(
        service.persist_posts_and_comments([post], [comment], "en")
    )

    assert len(docs) >= 1
    assert all(isinstance(d, Document) for d in docs)


def test_persist_posts_and_comments_uses_batch_queries_not_per_item_scalars() -> None:
    session = BatchFakeSession()
    service = _build_service(session, term="Tisza")
    posts = [_make_post(reddit_post_id=f"p{i}") for i in range(5)]
    comments = [_make_comment(reddit_comment_id=f"c{i}", reddit_post_id=f"p{i}") for i in range(5)]

    asyncio.run(service.persist_posts_and_comments(posts, comments, "en"))

    assert session.scalar_calls == 0


def test_persist_posts_and_comments_skips_non_matching_content() -> None:
    session = BatchFakeSession()
    service = _build_service(session, term="Tisza")
    post = CollectedPost(
        reddit_post_id="unrelated",
        subreddit="hungary",
        title="Unrelated post",
        body="Nothing relevant here",
        author_name="user",
        score=1,
        created_utc=_utc_now(),
        permalink="https://reddit.com/r/hungary/unrelated",
        raw_payload={},
    )

    docs = asyncio.run(service.persist_posts_and_comments([post], [], "en"))

    assert docs == []


def test_persist_posts_and_comments_reuses_existing_posts() -> None:
    existing_sub = Subreddit(name="hungary", is_enabled=True, is_core=True)
    existing_sub.id = "sub-hungary"
    existing_post = Post(
        reddit_post_id="p1",
        subreddit_id="sub-hungary",
        title="Tisza Peter campaign",
        body="",
        score=5,
        created_utc=_utc_now(),
        permalink="https://reddit.com/r/hungary/p1",
        raw_payload={},
    )
    existing_post.id = "post-p1"

    session = BatchFakeSession(
        existing_subreddits=[existing_sub],
        existing_posts=[existing_post],
    )
    service = _build_service(session, term="Tisza")
    post = _make_post()

    asyncio.run(service.persist_posts_and_comments([post], [], "en"))

    inserted_posts = [obj for obj in session._added if isinstance(obj, Post)]
    assert inserted_posts == []


class MatchFakeSession:
    def __init__(self) -> None:
        self._added: list[Any] = []
        self._flushed = 0

    def add(self, obj: Any) -> None:
        self._added.append(obj)

    async def flush(self) -> None:
        self._flushed += 1

    async def scalars(self, stmt: Any) -> Any:
        class _Result:
            def all(self) -> list:
                return []

        return _Result()


@dataclass
class FakeQueryRun:
    id: str = "run-1"
    language_filter: str = "en"


@dataclass
class FakeDocument:
    id: str
    full_text: str
    source_type: DocumentSourceType = DocumentSourceType.post


def test_match_and_persist_batch_returns_only_matched() -> None:
    from reddit_sentiment.db.models import QueryDocumentMatch

    session = MatchFakeSession()
    service = DocumentMatchService(session)  # type: ignore[arg-type]
    search_service = SearchService("Tisza")
    query_run = FakeQueryRun()

    matched_doc = FakeDocument(id="d1", full_text="Tisza Peter spoke today")
    unmatched_doc = FakeDocument(id="d2", full_text="unrelated content here")

    result = asyncio.run(
        service.match_and_persist_batch(
            query_run,  # type: ignore[arg-type]
            [matched_doc, unmatched_doc],  # type: ignore[arg-type, list-item]
            search_service,
        )
    )

    assert len(result) == 1
    assert result[0].id == "d1"
    assert session._flushed == 1
    persisted_matches = [obj for obj in session._added if isinstance(obj, QueryDocumentMatch)]
    assert len(persisted_matches) == 1
    assert persisted_matches[0].document_id == "d1"


def test_match_and_persist_batch_issues_single_flush() -> None:
    session = MatchFakeSession()
    service = DocumentMatchService(session)  # type: ignore[arg-type]
    search_service = SearchService("Tisza")
    query_run = FakeQueryRun()

    docs = [FakeDocument(id=f"d{i}", full_text="Tisza campaign") for i in range(10)]

    asyncio.run(
        service.match_and_persist_batch(
            query_run,  # type: ignore[arg-type]
            docs,  # type: ignore[arg-type, list-item]
            search_service,
        )
    )

    assert session._flushed == 1
