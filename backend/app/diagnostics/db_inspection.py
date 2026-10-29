"""Temporary private Lambda: fixed SELECTs, read-only transaction, metadata only.

No Alembic/ORM/seed imports and no user-supplied SQL. Never log connection info or errors.
"""

import re
import time

import psycopg
from psycopg.rows import dict_row

from app.config import settings

EXPECTED_ACCOUNT = "891447916595"
EXPECTED_REGION = "us-east-1"
FUNCTION_NAME = "meetings-db-inspection-lab6"
SESSION = "SELECT current_database() AS database, current_setting('transaction_read_only') AS read_only"
TABLES = """SELECT table_name, table_type FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('alembic_version', 'meetings', 'agendas')
ORDER BY table_name"""
COLUMNS = """SELECT table_name, column_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('alembic_version', 'meetings', 'agendas')
ORDER BY table_name, ordinal_position"""
CONSTRAINTS = """SELECT c.relname AS table_name, con.conname AS constraint_name,
con.contype AS constraint_type, con.convalidated AS validated,
pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN ('alembic_version', 'meetings', 'agendas')
ORDER BY c.relname, con.conname"""
REVISIONS = "SELECT version_num FROM public.alembic_version ORDER BY version_num"


class InspectionFailure(RuntimeError):
    """Only allowlisted diagnostic fields; never retain the underlying message."""

    def __init__(self, stage, exc, elapsed=0):
        sqlstate = getattr(exc, "sqlstate", None)
        sqlstate = sqlstate if isinstance(sqlstate, str) and re.fullmatch(r"[0-9A-Z]{5}", sqlstate) else None
        category = "operation_failed"
        if sqlstate and sqlstate.startswith("28"):
            stage, category = "authentication", "authentication_rejected"
        elif stage == "network/connect":
            # Inspect locally for classification only; never emit any message fragment.
            message = str(exc).lower()
            if "password authentication failed" in message or "no password supplied" in message:
                stage, category = "authentication", "authentication_rejected"
            elif "timeout" in message or "timed out" in message:
                category = "connection_timeout"
            elif "could not translate host" in message or "name or service not known" in message:
                category = "dns_resolution_failed"
            elif "ssl" in message or "certificate" in message:
                category = "tls_failure"
            elif "connection refused" in message:
                category = "connection_refused"
            else:
                category = "connection_failed"
        elif stage == "configuration":
            category = "invalid_configuration"
        elif sqlstate == "57014":
            category = "statement_timeout_or_cancel"
        self.diagnostic = {
            "stage": stage,
            "category": category,
            "error_type": type(exc).__name__
            if type(exc).__module__.startswith(("psycopg", "builtins"))
            else "Exception",
            "sqlstate": sqlstate,
            "elapsed_ms": round(elapsed * 1000),
        }
        super().__init__("inspection_failed")


def inspect_database(connect=psycopg.connect):
    started = time.monotonic()
    try:
        url = settings.sqlalchemy_url
        if not all((url.host, url.username, url.password, url.database)):
            raise ValueError("Missing database configuration")
    except Exception as exc:
        raise InspectionFailure("configuration", exc) from None
    if url.database != "meetings" or not (url.host or "").endswith(".us-east-1.rds.amazonaws.com"):
        raise InspectionFailure("configuration", ValueError()) from None
    try:
        connection = connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            dbname=url.database,
            connect_timeout=20,
            sslmode="require",
            row_factory=dict_row,
            options="-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000",
            autocommit=False,
        )
    except Exception as exc:
        raise InspectionFailure("network/connect", exc, time.monotonic() - started) from None
    stage = "transaction setup"
    try:
        session = connection.execute(SESSION).fetchone()
        if session["read_only"] != "on" or session["database"] != "meetings":
            raise RuntimeError("Read-only transaction was not established")
        stage = "metadata query"
        tables = connection.execute(TABLES).fetchall()
        version_table = next((t for t in tables if t["table_name"] == "alembic_version"), None)
        # An absent version table is evidence to review, never permission to initialize/stamp.
        revisions = None
        if version_table and version_table["table_type"] == "BASE TABLE":
            revisions = [r["version_num"] for r in connection.execute(REVISIONS).fetchall()]
        return {
            "status": "ok",
            "database": session["database"],
            "transaction_read_only": True,
            "tables": tables,
            "alembic_revisions": revisions,
            "columns": connection.execute(COLUMNS).fetchall(),
            "constraints": connection.execute(CONSTRAINTS).fetchall(),
        }
    except Exception as exc:
        raise InspectionFailure(stage, exc, time.monotonic() - started) from None
    finally:
        # Never commit, even on success. There are no DDL/DML statements or row reads besides version_num.
        try:
            connection.rollback()
        finally:
            connection.close()


def handler(event, context):
    if event != {"operation": "inspect_schema"}:
        return {"status": "error", "error": "unsupported_operation"}
    arn = getattr(context, "invoked_function_arn", "").split(":")
    if len(arn) < 7 or arn[3:7] != [EXPECTED_REGION, EXPECTED_ACCOUNT, "function", FUNCTION_NAME]:
        return {"status": "error", "error": "unexpected_execution_target"}
    try:
        return inspect_database()
    except InspectionFailure as exc:
        return {"status": "error", "error": "inspection_failed", **exc.diagnostic}
    except Exception as exc:
        # DB exception messages can contain credentials/SQL/data: never return or log them.
        return {"status": "error", "error": "inspection_failed", "error_type": type(exc).__name__}
