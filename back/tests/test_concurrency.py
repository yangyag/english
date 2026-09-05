from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from app.db import SessionLocal
from app.models import Base, StudyBatch, StudyState, Word
from app.schemas import SubmitIn
from app.study import submit
from test_today import payload


@pytest.mark.parametrize('same_id', [True, False])
def test_simultaneous_submissions_commit_once(same_id):
    with SessionLocal.begin() as db:
        db.add_all([Word(rank=i, word=str(i), meaning='test', example='test', example_ko='test') for i in range(1, 21)])
    first = payload()
    bodies = [first, first if same_id else payload()]
    barrier = Barrier(2)
    def run(body):
        try:
            with SessionLocal.begin() as db:
                barrier.wait(timeout=10)
                submit(db, date(2026, 8, 1), SubmitIn.model_validate(body), 'new')
            return 200
        except HTTPException as e:
            return e.status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = sorted(pool.map(run, bodies))
        assert statuses == ([200, 200] if same_id else [200, 409])
        with SessionLocal() as db:
            assert db.get(StudyState, 1).next_rank == 11
            assert db.scalar(select(func.count()).select_from(StudyBatch)) == 1
    finally:
        # This database is freshly created by conftest for this test run only.
        with SessionLocal.begin() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(delete(table))
