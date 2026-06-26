"""Add performance indexes for query_runs status polling, cache lookup, and document matches join"""

from alembic import op

revision = "0007_performance_indexes"
down_revision = "0006_sentiment_reuse_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_query_runs_status_started_at",
        "query_runs",
        ["status", "started_at"],
    )
    op.create_index(
        "ix_query_runs_query_id_status_started_at",
        "query_runs",
        ["query_id", "status", "started_at"],
    )
    op.create_index(
        "ix_query_document_matches_document_id",
        "query_document_matches",
        ["document_id"],
    )
    op.drop_index("ix_query_runs_query_id", table_name="query_runs", if_exists=True)


def downgrade() -> None:
    op.drop_index("ix_query_runs_status_started_at", table_name="query_runs")
    op.drop_index("ix_query_runs_query_id_status_started_at", table_name="query_runs")
    op.drop_index("ix_query_document_matches_document_id", table_name="query_document_matches")
    op.create_index("ix_query_runs_query_id", "query_runs", ["query_id"])
