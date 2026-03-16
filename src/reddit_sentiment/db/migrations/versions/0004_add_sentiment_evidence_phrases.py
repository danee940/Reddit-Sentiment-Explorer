"""Add evidence phrases to sentiment results"""

import sqlalchemy as sa
from alembic import op

revision = "0004_sentiment_evidence"
down_revision = "0003_expand_aggregate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sentiment_results",
        sa.Column("evidence_phrases", sa.JSON(), nullable=True),
    )
    op.execute(
        "UPDATE sentiment_results "
        "SET evidence_phrases = '[]'::json "
        "WHERE evidence_phrases IS NULL"
    )
    op.alter_column(
        "sentiment_results",
        "evidence_phrases",
        existing_type=sa.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("sentiment_results", "evidence_phrases")
