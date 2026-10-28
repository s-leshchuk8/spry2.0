"""add ai_suggestion to agendas

Revision ID: 5d5e3ded4830
Revises: 0003
Create Date: 2026-10-28 22:17:36.458927
"""
from alembic import op
import sqlalchemy as sa


revision = '5d5e3ded4830'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("agendas", sa.Column("ai_suggestion", postgresql.JSONB(), nullable=True))

def downgrade():
    op.drop_column("agendas", "ai_suggestion")
