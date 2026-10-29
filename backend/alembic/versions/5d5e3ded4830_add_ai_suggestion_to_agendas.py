"""add ai_suggestion to agendas

Revision ID: 5d5e3ded4830
Revises: 0003
Create Date: 2026-10-28 22:17:36.458927
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5d5e3ded4830"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    if "agendas" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "agendas",
            sa.Column(
                "meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.Column("final_agenda", sa.JSON(), nullable=False),
            sa.Column("ai_suggestion", postgresql.JSONB(), nullable=True),
        )
    elif "ai_suggestion" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("agendas")}:
        op.add_column("agendas", sa.Column("ai_suggestion", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("agendas", "ai_suggestion")
