"""Add execution safety constraints"""

from alembic import op

revision = "0002_execution_guards"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_queries_normalized_term", "queries", ["normalized_term"])
    op.create_unique_constraint("uq_documents_source", "documents", ["source_type", "source_id"])
    op.create_unique_constraint(
        "uq_query_document_matches_run_document",
        "query_document_matches",
        ["query_run_id", "document_id"],
    )
    op.create_unique_constraint(
        "uq_sentiment_results_run_document",
        "sentiment_results",
        ["query_run_id", "document_id"],
    )
    op.create_unique_constraint(
        "uq_aggregates_run_type",
        "aggregates",
        ["query_run_id", "aggregate_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_aggregates_run_type", "aggregates", type_="unique")
    op.drop_constraint(
        "uq_sentiment_results_run_document",
        "sentiment_results",
        type_="unique",
    )
    op.drop_constraint(
        "uq_query_document_matches_run_document",
        "query_document_matches",
        type_="unique",
    )
    op.drop_constraint("uq_documents_source", "documents", type_="unique")
    op.drop_constraint("uq_queries_normalized_term", "queries", type_="unique")
