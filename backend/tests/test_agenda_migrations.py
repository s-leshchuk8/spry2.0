"""Forward-revision rehearsal on a rollback-only schema in the disposable PostgreSQL DB.

This does not bypass or repair the historical predecessor.
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from tests.conftest import engine

pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Needs disposable PostgreSQL")


@pytest.mark.parametrize("existing", ["absent", "compatible", "incompatible", "wrong_type", "missing_fk"])
def test_forward_migration_preserves_history(existing):
    path = Path(__file__).parents[1] / "alembic/versions/0004_reviewed_agendas.py"
    spec = importlib.util.spec_from_file_location("agenda_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    name = "lab6_" + uuid4().hex
    with engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.execute(text(f'CREATE SCHEMA "{name}"'))
            conn.execute(text(f'SET LOCAL search_path TO "{name}"'))
            conn.execute(text("CREATE TABLE meetings (id UUID PRIMARY KEY)"))
            if existing == "compatible":
                conn.execute(
                    text(
                        "CREATE TABLE agendas (meeting_id UUID PRIMARY KEY REFERENCES meetings(id) "
                        "ON DELETE CASCADE, final_agenda JSON NOT NULL)"
                    )
                )
            elif existing in {"wrong_type", "missing_fk"}:
                final_type = "TEXT" if existing == "wrong_type" else "JSON"
                conn.execute(
                    text(
                        "CREATE TABLE agendas (meeting_id UUID PRIMARY KEY, "
                        f"final_agenda {final_type} NOT NULL)"
                    )
                )
            elif existing == "incompatible":
                conn.execute(text("CREATE TABLE agendas (legacy_data TEXT)"))
                conn.execute(text("INSERT INTO agendas VALUES ('keep me')"))
            with Operations.context(MigrationContext.configure(conn)):
                if existing == "incompatible":
                    with pytest.raises(RuntimeError, match="reviewed data migration"):
                        revision.upgrade()
                    assert conn.scalar(text("SELECT legacy_data FROM agendas")) == "keep me"
                elif existing in {"wrong_type", "missing_fk"}:
                    with pytest.raises(RuntimeError, match="reviewed reconciliation"):
                        revision.upgrade()
                    assert "ai_suggestion" not in {c["name"] for c in inspect(conn).get_columns("agendas")}
                else:
                    revision.upgrade()
                    revision.upgrade()  # Safe reconciliation when schema is already compatible.
                    assert {c["name"] for c in inspect(conn).get_columns("agendas")} == {
                        "meeting_id",
                        "final_agenda",
                        "ai_suggestion",
                    }
                    assert inspect(conn).get_foreign_keys("agendas")[0]["options"]["ondelete"] == "CASCADE"
        finally:
            transaction.rollback()
