from types import SimpleNamespace as NS

import pytest

from app.config import settings
from app.diagnostics import db_inspection as module

CONTEXT = NS(
    invoked_function_arn="arn:aws:lambda:us-east-1:891447916595:function:meetings-db-inspection-lab6"
)


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, version=True, read_only="on", fail=False):
        self.queries = []
        self.version, self.read_only, self.fail = version, read_only, fail
        self.rolled_back = self.closed = False

    def execute(self, sql):
        self.queries.append(sql)
        assert sql.lstrip().upper().startswith("SELECT ")
        if sql == module.SESSION:
            return Result([{"database": "meetings", "read_only": self.read_only}])
        if self.fail:
            raise RuntimeError("password=do-not-print")
        if sql == module.TABLES:
            return Result(
                [{"table_name": "alembic_version", "table_type": "BASE TABLE"}] if self.version else []
            )
        if sql == module.REVISIONS:
            return Result([{"version_num": "0003"}])
        return Result([])

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def target(monkeypatch):
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "db_host", "meetings-db.cluster-test.us-east-1.rds.amazonaws.com")
    monkeypatch.setattr(settings, "db_name", "meetings")


def test_fixed_queries_and_read_only_connection():
    connection = Connection()
    kwargs = {}

    def connect(**values):
        kwargs.update(values)
        return connection

    result = module.inspect_database(connect)
    assert result["alembic_revisions"] == ["0003"]
    assert result["transaction_read_only"]
    assert "default_transaction_read_only=on" in kwargs["options"]
    assert "statement_timeout=5000" in kwargs["options"]
    assert kwargs["sslmode"] == "require" and kwargs["autocommit"] is False
    assert connection.rolled_back and connection.closed
    assert set(connection.queries) == {
        module.SESSION,
        module.TABLES,
        module.COLUMNS,
        module.CONSTRAINTS,
        module.REVISIONS,
    }


def test_no_version_table_is_not_assumed_unapplied():
    connection = Connection(version=False)
    result = module.inspect_database(lambda **_: connection)
    assert result["alembic_revisions"] is None and module.REVISIONS not in connection.queries


@pytest.mark.parametrize("connection", [Connection(read_only="off"), Connection(fail=True)])
def test_failures_always_rollback_and_close(connection):
    with pytest.raises(RuntimeError):
        module.inspect_database(lambda **_: connection)
    assert connection.rolled_back and connection.closed


def test_handler_rejects_arbitrary_sql_and_wrong_account(monkeypatch):
    monkeypatch.setattr(module, "inspect_database", lambda: pytest.fail("DB accessed"))
    assert (
        module.handler({"operation": "inspect_schema", "sql": "DROP TABLE meetings"}, CONTEXT)["error"]
        == "unsupported_operation"
    )
    wrong = NS(
        invoked_function_arn="arn:aws:lambda:us-east-1:968053399627:function:meetings-db-inspection-lab6"
    )
    assert module.handler({"operation": "inspect_schema"}, wrong)["error"] == "unexpected_execution_target"
    http = {"requestContext": {"http": {"method": "POST"}}}
    assert module.handler(http, CONTEXT)["error"] == "unsupported_operation"


def test_handler_never_returns_exception_details(monkeypatch, caplog):
    def fail():
        raise RuntimeError("password=do-not-print")

    monkeypatch.setattr(module, "inspect_database", fail)
    result = module.handler({"operation": "inspect_schema"}, CONTEXT)
    assert result == {"status": "error", "error": "inspection_failed", "error_type": "RuntimeError"}
    assert "do-not-print" not in str(result) + caplog.text


def test_disposable_postgresql_enforces_read_only():
    """Optional real-server proof, only in the dedicated local inspection-test container."""
    import os

    import psycopg
    from sqlalchemy import make_url

    value = os.environ.get("SPRY_DISPOSABLE_INSPECTION_URL")
    if not value:
        pytest.skip("Dedicated disposable inspection PostgreSQL not configured")
    url = make_url(value)
    if (url.host, url.port, url.database) != ("127.0.0.1", 55437, "meetings"):
        pytest.fail("Expected only the dedicated local inspection test endpoint")

    def connect(**kwargs):
        # The disposable localhost container has no TLS certificate; production still requires TLS.
        assert kwargs["sslmode"] == "require"
        kwargs.update(
            host=url.host, port=url.port, user=url.username, password=url.password, sslmode="disable"
        )
        connection = psycopg.connect(**kwargs)
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            connection.execute("CREATE TABLE inspection_must_not_write (id integer)")
        connection.rollback()
        return connection

    result = module.inspect_database(connect)
    assert result["transaction_read_only"] is True
    assert result["alembic_revisions"] == ["0003"]
    assert any(c["constraint_type"] == "f" for c in result["constraints"])


@pytest.mark.parametrize(
    ("message", "stage", "category"),
    [
        ("connection timeout password=secret", "network/connect", "connection_timeout"),
        ("password authentication failed secret", "authentication", "authentication_rejected"),
        ("could not translate host secret", "network/connect", "dns_resolution_failed"),
        ("connection refused secret", "network/connect", "connection_refused"),
    ],
)
def test_connection_diagnostics(message, stage, category, monkeypatch, caplog):
    import psycopg

    def connect(**kwargs):
        raise psycopg.OperationalError(message)

    monkeypatch.setattr(module, "inspect_database", lambda: original(connect))
    result = module.handler({"operation": "inspect_schema"}, CONTEXT)
    assert result["stage"] == stage and result["category"] == category
    assert result["error_type"] == "OperationalError"
    assert "secret" not in str(result) + caplog.text


original = module.inspect_database


def test_missing_configuration(monkeypatch):
    monkeypatch.setattr(settings, "db_password", "")
    with pytest.raises(module.InspectionFailure) as caught:
        module.inspect_database(lambda **_: pytest.fail("connected"))
    assert caught.value.diagnostic["stage"] == "configuration"


def test_sqlstate_authentication():
    import psycopg

    result = module.InspectionFailure("network/connect", psycopg.errors.InvalidPassword("secret"))
    assert result.diagnostic["sqlstate"] == "28P01"
    assert result.diagnostic["stage"] == "authentication"
    assert "secret" not in str(result.diagnostic)


def test_transaction_and_query_failure_stages():
    for connection, stage in [
        (Connection(read_only="off"), "transaction setup"),
        (Connection(fail=True), "metadata query"),
    ]:
        with pytest.raises(module.InspectionFailure) as caught:
            module.inspect_database(lambda connection=connection, **_: connection)
        assert caught.value.diagnostic["stage"] == stage
        assert connection.rolled_back and connection.closed
