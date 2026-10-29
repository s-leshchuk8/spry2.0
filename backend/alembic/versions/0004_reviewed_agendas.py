"""Forward reconciliation after the historical agenda revision.

The historical predecessor is intentionally unchanged pending deployment-history verification.
Fresh upgrades through that broken predecessor remain blocked; see docs/lab6-migrations.md.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_reviewed_agendas"
down_revision = "5d5e3ded4830"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "agendas" not in inspector.get_table_names():
        op.create_table(
            "agendas",
            sa.Column(
                "meeting_id", sa.Uuid(), sa.ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.Column("final_agenda", sa.JSON(), nullable=False),
            sa.Column("ai_suggestion", postgresql.JSONB(), nullable=True),
        )
        return
    metadata = {c["name"]: c for c in inspector.get_columns("agendas")}
    columns = set(metadata)
    # Never silently overwrite an unknown pre-existing agenda schema or its data.
    if not {"meeting_id", "final_agenda"}.issubset(columns):
        raise RuntimeError(
            "Existing agendas schema needs a reviewed data migration; see docs/lab6-migrations.md"
        )
    pk = inspector.get_pk_constraint("agendas")["constrained_columns"]
    if pk != ["meeting_id"]:
        raise RuntimeError("Expected one agenda per meeting; review existing data before migration")
    if (
        not isinstance(metadata["meeting_id"]["type"], sa.Uuid)
        or metadata["meeting_id"]["nullable"]
        or not isinstance(metadata["final_agenda"]["type"], sa.JSON)
        or metadata["final_agenda"]["nullable"]
    ):
        raise RuntimeError("Existing agenda column types/nullability need reviewed reconciliation")
    if "ai_suggestion" in metadata and (
        not isinstance(metadata["ai_suggestion"]["type"], postgresql.JSONB)
        or not metadata["ai_suggestion"]["nullable"]
    ):
        raise RuntimeError("Existing suggestion type/nullability needs reviewed reconciliation")
    if not any(
        fk["constrained_columns"] == ["meeting_id"]
        and fk["referred_table"] == "meetings"
        and fk["referred_columns"] == ["id"]
        and fk.get("referred_schema") in (None, inspector.default_schema_name)
        and fk.get("options", {}).get("ondelete", "").upper() == "CASCADE"
        for fk in inspector.get_foreign_keys("agendas")
    ):
        raise RuntimeError("Existing agenda foreign key needs reviewed reconciliation")
    if "ai_suggestion" not in columns:
        op.add_column("agendas", sa.Column("ai_suggestion", postgresql.JSONB(), nullable=True))


def downgrade():
    raise RuntimeError("Agenda downgrade would delete reviewed data; use a separately reviewed recovery plan")
