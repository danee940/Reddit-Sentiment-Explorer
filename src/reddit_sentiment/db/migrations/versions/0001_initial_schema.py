"""Initial schema"""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


query_run_status = sa.Enum(
    "pending",
    "running",
    "completed",
    "failed",
    name="queryrunstatus",
    native_enum=False,
)
document_source_type = sa.Enum(
    "post",
    "comment",
    name="documentsourcetype",
    native_enum=False,
)
sentiment_label = sa.Enum(
    "very_negative",
    "negative",
    "neutral",
    "positive",
    "very_positive",
    name="sentimentlabel",
    native_enum=False,
)
aggregate_type = sa.Enum(
    "overview",
    "sentiment_distribution",
    "sentiment_timeline",
    "volume_timeline",
    "subreddit_breakdown",
    "sentiment_heatmap",
    "rolling_sentiment_timeline",
    "phrase_breakdown",
    "spike_events",
    name="aggregatetype",
    native_enum=False,
    length=32,
)


def upgrade() -> None:
    op.create_table(
        "queries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("raw_term", sa.String(length=255), nullable=False),
        sa.Column("normalized_term", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_queries_normalized_term", "queries", ["normalized_term"])

    op.create_table(
        "subreddits",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_core", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "query_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("query_id", sa.String(length=36), sa.ForeignKey("queries.id"), nullable=False),
        sa.Column("status", query_run_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("scope_config", sa.JSON(), nullable=False),
        sa.Column("match_strategy", sa.String(length=100), nullable=False),
        sa.Column("language_filter", sa.String(length=50), nullable=False),
        sa.Column("data_fresh_until", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_query_runs_query_id", "query_runs", ["query_id"])

    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reddit_post_id", sa.String(length=50), nullable=False),
        sa.Column(
            "subreddit_id",
            sa.String(length=36),
            sa.ForeignKey("subreddits.id"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(length=100)),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("permalink", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("reddit_post_id"),
    )
    op.create_index("ix_posts_reddit_post_id", "posts", ["reddit_post_id"])
    op.create_index("ix_posts_subreddit_id", "posts", ["subreddit_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("reddit_comment_id", sa.String(length=50), nullable=False),
        sa.Column("post_id", sa.String(length=36), sa.ForeignKey("posts.id")),
        sa.Column(
            "subreddit_id",
            sa.String(length=36),
            sa.ForeignKey("subreddits.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(length=100)),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("permalink", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("reddit_comment_id"),
    )
    op.create_index("ix_comments_reddit_comment_id", "comments", ["reddit_comment_id"])
    op.create_index("ix_comments_subreddit_id", "comments", ["subreddit_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_type", document_source_type, nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column(
            "subreddit_id",
            sa.String(length=36),
            sa.ForeignKey("subreddits.id"),
            nullable=False,
        ),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("detected_language", sa.String(length=20)),
        sa.Column("language_confidence", sa.Float()),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("permalink", sa.Text()),
    )
    op.create_index("ix_documents_created_utc", "documents", ["created_utc"])
    op.create_index("ix_documents_subreddit_id", "documents", ["subreddit_id"])

    op.create_table(
        "query_document_matches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "query_run_id",
            sa.String(length=36),
            sa.ForeignKey("query_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("match_type", sa.String(length=50), nullable=False),
        sa.Column("matched_terms", sa.JSON(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
    )
    op.create_index(
        "ix_query_document_matches_query_run_id",
        "query_document_matches",
        ["query_run_id"],
    )

    op.create_table(
        "sentiment_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "query_run_id",
            sa.String(length=36),
            sa.ForeignKey("query_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(length=36),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("provider_version", sa.String(length=100), nullable=False),
        sa.Column("label", sentiment_label, nullable=False),
        sa.Column("score_value", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sentiment_results_query_run_id", "sentiment_results", ["query_run_id"])

    op.create_table(
        "aggregates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "query_run_id",
            sa.String(length=36),
            sa.ForeignKey("query_runs.id"),
            nullable=False,
        ),
        sa.Column("aggregate_type", aggregate_type, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_aggregates_query_run_id", "aggregates", ["query_run_id"])


def downgrade() -> None:
    op.drop_index("ix_aggregates_query_run_id", table_name="aggregates")
    op.drop_table("aggregates")
    op.drop_index("ix_sentiment_results_query_run_id", table_name="sentiment_results")
    op.drop_table("sentiment_results")
    op.drop_index("ix_query_document_matches_query_run_id", table_name="query_document_matches")
    op.drop_table("query_document_matches")
    op.drop_index("ix_documents_subreddit_id", table_name="documents")
    op.drop_index("ix_documents_created_utc", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_comments_subreddit_id", table_name="comments")
    op.drop_index("ix_comments_reddit_comment_id", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_posts_subreddit_id", table_name="posts")
    op.drop_index("ix_posts_reddit_post_id", table_name="posts")
    op.drop_table("posts")
    op.drop_index("ix_query_runs_query_id", table_name="query_runs")
    op.drop_table("query_runs")
    op.drop_table("subreddits")
    op.drop_index("ix_queries_normalized_term", table_name="queries")
    op.drop_table("queries")
