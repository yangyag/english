import os
from uuid import uuid4
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Always use a newly created LOCAL database, never a configured production schema.
from local_testing import configure_local
configure_local()
from app.config import get_settings

admin_url = get_settings().database_url
test_database = "english_test_" + uuid4().hex
admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
with admin.connect() as conn:
    conn.exec_driver_sql(f'CREATE DATABASE "{test_database}"')
os.environ["PGDATABASE"] = test_database
get_settings.cache_clear()

from app.clock import get_today
from app.db import engine, get_db, init_db
from app.main import app
from app.models import Word


@pytest.fixture(scope="session", autouse=True)
def _tables():
    init_db()
    yield
    engine.dispose()
    with admin.connect() as conn:
        conn.exec_driver_sql(f'DROP DATABASE "{test_database}" WITH (FORCE)')
    admin.dispose()


@pytest.fixture
def db():
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture
def clock():
    class Frozen:
        today = date(2026, 8, 1)
    return Frozen


@pytest.fixture
def words(db):
    db.add_all([Word(rank=i, word=f"w{i}", meaning=f"뜻{i}", example=f"ex {i}", example_ko=f"예{i}") for i in range(1, 31)])
    db.flush()


@pytest.fixture
def client(db, clock, words):
    def override_db():
        yield db
        db.flush()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_today] = lambda: clock.today
    # Startup migration is tested separately; running it during a transaction
    # would take the same advisory lock on another connection.
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
