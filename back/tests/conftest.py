import os

# 테스트는 실제 학습 데이터(english 스키마)와 격리한다.
# 실제 env 변수는 .env 파일보다 우선하므로, app 임포트 전에 지정한다.
os.environ.setdefault("PGSCHEMA", "english_test")

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import engine, get_db, init_db
from app.main import app
from app.models import Word


@pytest.fixture(scope="session", autouse=True)
def _tables() -> None:
    init_db()


@pytest.fixture
def db() -> Session:
    connection = engine.connect()
    trans = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        if trans.is_active:
            trans.rollback()
        connection.close()


@pytest.fixture
def clock():
    class Frozen:
        today = date(2026, 8, 1)

    return Frozen


@pytest.fixture
def words(db: Session) -> None:
    for i in range(1, 31):
        db.merge(Word(rank=i, word=f"w{i}", meaning=f"뜻{i}", example=f"ex {i}", example_ko=f"예{i}"))
    db.flush()


@pytest.fixture
def client(db: Session, clock, words) -> TestClient:
    def override_db():
        try:
            yield db
        finally:
            if db.in_transaction():
                db.flush()
                db.expire_all()

    def override_today() -> date:
        return clock.today

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_today] = override_today
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
