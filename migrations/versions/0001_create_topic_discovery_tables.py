"""Create topic discovery persistence tables.

Revision ID: 0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "topic_candidate",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.String(length=300), nullable=False),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topic_candidate_normalized_title", "topic_candidate", ["normalized_title"])
    op.create_index("ix_topic_candidate_dedupe_key", "topic_candidate", ["dedupe_key"], unique=True)

    op.create_table(
        "topic_source",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("external_id", sa.String(length=300), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topic_candidate_id"], ["topic_candidate.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_kind", "external_id", name="uq_topic_source_external"),
    )
    op.create_index("ix_topic_source_topic_candidate_id", "topic_source", ["topic_candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_topic_source_topic_candidate_id", table_name="topic_source")
    op.drop_table("topic_source")
    op.drop_index("ix_topic_candidate_dedupe_key", table_name="topic_candidate")
    op.drop_index("ix_topic_candidate_normalized_title", table_name="topic_candidate")
    op.drop_table("topic_candidate")
