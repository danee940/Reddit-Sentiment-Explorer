from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reddit_sentiment.core.enums import (
    AggregateType,
    DocumentSourceType,
    QueryRunStatus,
    SentimentLabel,
)
from reddit_sentiment.core.languages import DEFAULT_CONTENT_LANGUAGE
from reddit_sentiment.db.base import Base


def uuid_str() -> str:
    return str(uuid4())


class Query(Base):
    __tablename__ = "queries"
    __table_args__ = (UniqueConstraint("normalized_term"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    raw_term: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_term: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    runs: Mapped[list[QueryRun]] = relationship(back_populates="query")


class QueryRun(Base):
    __tablename__ = "query_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    query_id: Mapped[str] = mapped_column(ForeignKey("queries.id"), index=True, nullable=False)
    status: Mapped[QueryRunStatus] = mapped_column(
        Enum(QueryRunStatus, native_enum=False),
        default=QueryRunStatus.pending,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope_config: Mapped[dict] = mapped_column(JSON, default=dict)
    match_strategy: Mapped[str] = mapped_column(String(100), default="phrase_then_tokens")
    language_filter: Mapped[str] = mapped_column(String(50), default=DEFAULT_CONTENT_LANGUAGE)
    sentiment_provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sentiment_provider_version: Mapped[str] = mapped_column(String(100), nullable=False)
    data_fresh_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    query: Mapped[Query] = relationship(back_populates="runs")
    matches: Mapped[list[QueryDocumentMatch]] = relationship(back_populates="query_run")
    sentiments: Mapped[list[SentimentResult]] = relationship(back_populates="query_run")
    aggregates: Mapped[list[Aggregate]] = relationship(back_populates="query_run")


class Subreddit(Base):
    __tablename__ = "subreddits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("reddit_post_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    reddit_post_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    subreddit_id: Mapped[str] = mapped_column(
        ForeignKey("subreddits.id"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    author_name: Mapped[str | None] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer, default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    permalink: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("reddit_comment_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    reddit_comment_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id"))
    subreddit_id: Mapped[str] = mapped_column(
        ForeignKey("subreddits.id"),
        index=True,
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(100))
    score: Mapped[int] = mapped_column(Integer, default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    permalink: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_type", "source_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_type: Mapped[DocumentSourceType] = mapped_column(
        Enum(DocumentSourceType, native_enum=False),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    subreddit_id: Mapped[str] = mapped_column(
        ForeignKey("subreddits.id"),
        index=True,
        nullable=False,
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_language: Mapped[str | None] = mapped_column(String(20))
    language_confidence: Mapped[float | None] = mapped_column(Float)
    created_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    permalink: Mapped[str | None] = mapped_column(Text)

    matches: Mapped[list[QueryDocumentMatch]] = relationship(back_populates="document")
    sentiments: Mapped[list[SentimentResult]] = relationship(back_populates="document")


class QueryDocumentMatch(Base):
    __tablename__ = "query_document_matches"
    __table_args__ = (UniqueConstraint("query_run_id", "document_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    query_run_id: Mapped[str] = mapped_column(
        ForeignKey("query_runs.id"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    match_type: Mapped[str] = mapped_column(String(50), nullable=False)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, default=list)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0)

    query_run: Mapped[QueryRun] = relationship(back_populates="matches")
    document: Mapped[Document] = relationship(back_populates="matches")


class SentimentResult(Base):
    __tablename__ = "sentiment_results"
    __table_args__ = (
        UniqueConstraint("query_run_id", "document_id"),
        Index(
            "ix_sentiment_results_reuse_lookup",
            "document_id",
            "provider_name",
            "provider_version",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    query_run_id: Mapped[str] = mapped_column(
        ForeignKey("query_runs.id"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_version: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[SentimentLabel] = mapped_column(
        Enum(SentimentLabel, native_enum=False),
        nullable=False,
    )
    score_value: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    rationale: Mapped[str | None] = mapped_column(Text)
    evidence_phrases: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    query_run: Mapped[QueryRun] = relationship(back_populates="sentiments")
    document: Mapped[Document] = relationship(back_populates="sentiments")


class Aggregate(Base):
    __tablename__ = "aggregates"
    __table_args__ = (UniqueConstraint("query_run_id", "aggregate_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    query_run_id: Mapped[str] = mapped_column(
        ForeignKey("query_runs.id"),
        index=True,
        nullable=False,
    )
    aggregate_type: Mapped[AggregateType] = mapped_column(
        Enum(AggregateType, native_enum=False, length=32),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    query_run: Mapped[QueryRun] = relationship(back_populates="aggregates")
