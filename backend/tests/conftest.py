"""Fresh in-memory DB, or explicitly named disposable local PostgreSQL; never TEST_DATABASE_URL."""

import os
from collections.abc import Iterator
from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import DateTime, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

from app.config import settings
from app.db import Base, get_db
from app.main import app

test_url = os.environ.get("SPRY_DISPOSABLE_TEST_DATABASE_URL")
if test_url:
    url = make_url(test_url)
    if url.host != "127.0.0.1" or url.database != "spry_lab6_disposable":
        raise RuntimeError("Only the explicitly disposable local Lab 6 database is accepted")
    engine = create_engine(url)
else:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


class SQLiteAwareDateTime(TypeDecorator):
    """Restore UTC awareness SQLite lacks; PostgreSQL tests use native TIMESTAMPTZ."""

    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def foreign_keys(connection, record):
    if engine.dialect.name == "sqlite":
        connection.execute("PRAGMA foreign_keys=ON")


@pytest.fixture(scope="session")
def schema() -> Iterator[None]:
    if engine.dialect.name == "sqlite":
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, DateTime):
                    column.type = SQLiteAwareDateTime()
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(schema, monkeypatch) -> Iterator[TestClient]:
    # Integration tests explicitly opt into Cognito in test_auth's fixture.
    if not settings.cognito_jwks:
        monkeypatch.setattr(settings, "cognito_user_pool_id", "")

    def override_get_db() -> Iterator[Session]:
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
