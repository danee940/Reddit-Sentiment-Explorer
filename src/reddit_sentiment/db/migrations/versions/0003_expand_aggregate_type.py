"""Expand aggregate type length for new analytics"""

import sqlalchemy as sa
from alembic import op

revision = "0003_expand_aggregate"
down_revision = "0002_execution_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "aggregates",
        "aggregate_type",
        existing_type=sa.String(length=22),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "aggregates",
        "aggregate_type",
        existing_type=sa.String(length=32),
        type_=sa.String(length=22),
        existing_nullable=False,
    )
