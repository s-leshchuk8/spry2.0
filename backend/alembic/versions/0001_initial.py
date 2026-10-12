"""Create meetings, participants and meeting_participants.

Revision ID: 0001
Revises:
Create Date: 2026-09-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("call_link", sa.String(2048), nullable=True),
        sa.Column("place", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "meeting_participants",
        sa.Column(
            "meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "participant_id",
            sa.Uuid(),
            sa.ForeignKey("participants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_meeting_participants_participant_id", "meeting_participants", ["participant_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_participants_participant_id", table_name="meeting_participants")
    op.drop_table("meeting_participants")
    op.drop_table("participants")
    op.drop_table("meetings")
