from datetime import date, datetime, timezone
from sqlalchemy import func, select
from app.migration import migrate_legacy
from app.models import BatchResult, StudyBatch, StudySession, StudyState, WordResult


def test_legacy_import_preserves_dates_answers_and_cursor(client, db):
    session = StudySession(study_date=date(2026, 7, 31), new_from_rank=1, new_to_rank=10)
    db.add(session)
    db.flush()
    db.add(StudyState(id=1, next_rank=21, last_study_date=date(2026, 8, 1)))
    for i in range(1, 21):
        # One legacy session may span KST midnight; use actual completion times.
        stamp = datetime(2026, 7, 31, 14 if i <= 10 else 15, tzinfo=timezone.utc)
        db.add(WordResult(session_id=session.id, rank=i, kind='new', known=i % 2 == 0, studied_at=stamp))
    db.add(WordResult(session_id=session.id, rank=1, kind='review', known=False,
                      studied_at=datetime(2026, 7, 31, 15, tzinfo=timezone.utc)))
    db.flush()
    assert migrate_legacy(db) == 21
    assert migrate_legacy(db) == 0
    assert db.scalar(select(func.count()).select_from(WordResult)) == 21
    assert db.scalar(select(func.count()).select_from(BatchResult)) == 21
    assert db.get(StudyState, 1).next_rank == 21
    assert db.scalar(select(StudyBatch).where(StudyBatch.kind == 'review')).source_date is None
    assert client.get('/v1/calendar?month=2026-07').json()['days'][0]['new_count'] == 10
    assert client.get('/v1/calendar?month=2026-08').json()['days'][0] == dict(date='2026-08-01', new_count=10, review_count=1)
    results = client.get('/v1/calendar/2026-07-31').json()['results']
    assert results[0]['known'] is False and results[1]['known'] is True
    # After a pre-opening rollback, the legacy app may append to the same day.
    db.add(WordResult(session_id=session.id, rank=21, kind='new', known=True,
                      studied_at=datetime(2026, 7, 31, 16, tzinfo=timezone.utc)))
    db.flush()
    assert migrate_legacy(db) == 1
    assert migrate_legacy(db) == 0
    assert db.scalar(select(func.count()).select_from(BatchResult)) == 22


def test_missing_history_does_not_invent_dates(client, db):
    db.add(StudyState(id=1, next_rank=11, last_study_date=date(2026, 7, 1)))
    db.flush()
    assert migrate_legacy(db) == 0
    progress = client.get('/v1/progress').json()
    assert progress['learned_count'] == progress['undated_learned_count'] == 10
    assert progress['study_days'] == 0
    assert client.get('/v1/today').json()['new'][0]['rank'] == 11
    assert client.get('/v1/today').json()['review'] == []
