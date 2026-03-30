"""Add sentiment provider identity to query runs"""

import sqlalchemy as sa
from alembic import op

revision = "0005_run_sent_provider"
down_revision = "0004_sentiment_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_runs",
        sa.Column("sentiment_provider_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "query_runs",
        sa.Column("sentiment_provider_version", sa.String(length=100), nullable=True),
    )
    op.execute(
        "UPDATE query_runs SET sentiment_provider_name = 'mock', "
        "sentiment_provider_version = 'heuristic-v3' "
        "WHERE sentiment_provider_name IS NULL"
    )
    op.alter_column(
        "query_runs",
        "sentiment_provider_name",
        existing_type=sa.String(length=100),
        nullable=False,
    )
    op.alter_column(
        "query_runs",
        "sentiment_provider_version",
        existing_type=sa.String(length=100),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("query_runs", "sentiment_provider_version")
    op.drop_column("query_runs", "sentiment_provider_name")
