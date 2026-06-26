"""Add sentiment result reuse lookup index"""

from alembic import op

revision = "0006_sentiment_reuse_index"
down_revision = "0005_run_sent_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_sentiment_results_reuse_lookup",
        "sentiment_results",
        ["document_id", "provider_name", "provider_version", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sentiment_results_reuse_lookup", table_name="sentiment_results")
