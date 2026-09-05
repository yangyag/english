from datetime import date
from uuid import uuid4
import pytest
from sqlalchemy import delete
from app.models import Word


def payload(start=1, end=10, day="2026-08-01", source=None, known=True):
    return dict(request_id=str(uuid4()), study_date=day, source_date=source,
                results=[dict(rank=i, known=known) for i in range(start, end + 1)])


def post(client, start=1, end=10, day="2026-08-01", source=None, known=True):
    return client.post('/v1/today/review' if source else '/v1/today/new', json=payload(start, end, day, source, known))


def test_visit_does_not_record_learning(client):
    body = client.get('/v1/today').json()
    assert len(body['new']) == 10 and body['review'] == []
    assert client.get('/v1/calendar?month=2026-08').json()['days'] == []


def test_unlimited_new_and_optional_review(client, clock):
    assert post(client).status_code == 200
    assert post(client, 11, 20).status_code == 200
    clock.today = date(2026, 8, 7)
    plan = client.get('/v1/today').json()
    assert plan['review_total'] == 20
    assert plan['review_source_date'] == '2026-08-01'
    assert post(client, 21, 30, '2026-08-07').status_code == 200
    assert client.get('/v1/today').json()['review_total'] == 20
    clock.today = date(2026, 8, 8)
    plan = client.get('/v1/today').json()
    assert plan['review_source_date'] == '2026-08-07'
    assert [w['rank'] for w in plan['review']] == list(range(21, 31))


def test_review_resume_across_days_and_exhaustion(client, clock):
    for start in (1, 11, 21):
        assert post(client, start, start + 9).status_code == 200
    clock.today = date(2026, 8, 3)
    assert post(client, 1, 10, '2026-08-03', '2026-08-01', False).status_code == 200
    clock.today = date(2026, 9, 1)
    plan = client.get('/v1/today').json()
    assert plan['new'] == [] and plan['review_completed'] == 10
    assert plan['review_source_date'] == '2026-08-01'
    for start in (11, 21):
        assert post(client, start, start + 9, '2026-09-01', '2026-08-01').status_code == 200
    plan = client.get('/v1/today').json()
    assert plan['review'] == [] and plan['review_completed'] == 30
    clock.today = date(2026, 9, 2)
    assert client.get('/v1/today').json()['review'] == []
    assert client.get('/v1/progress').json()['learned_count'] == 30


def test_retry_after_midnight_and_conflicting_id(client, clock):
    body = payload()
    assert client.post('/v1/today/new', json=body).status_code == 200
    clock.today = date(2026, 8, 2)
    assert client.post('/v1/today/new', json=body).status_code == 200
    body['results'][0]['known'] = False
    assert client.post('/v1/today/new', json=body).status_code == 409
    assert client.get('/v1/progress').json()['learned_count'] == 10


def test_stale_new_request_does_not_advance(client, clock):
    stale = payload()
    clock.today = date(2026, 8, 2)
    assert client.post('/v1/today/new', json=stale).status_code == 409
    assert client.get('/v1/progress').json()['learned_count'] == 0


@pytest.mark.parametrize('ranks', [[1], list(range(2, 12)), [1] * 10])
def test_whole_batch_required(client, ranks):
    body = payload()
    body['results'] = [dict(rank=r, known=True) for r in ranks]
    assert client.post('/v1/today/new', json=body).status_code == 409
    assert client.get('/v1/progress').json()['learned_count'] == 0


def test_fewer_than_ten_and_empty_vocabulary(client, db):
    db.execute(delete(Word).where(Word.rank > 3))
    assert len(client.get('/v1/today').json()['new']) == 3
    assert post(client, 1, 3).status_code == 200
    assert client.get('/v1/today').json()['new'] == []


def test_empty_db(client, db):
    db.execute(delete(Word))
    assert client.get('/v1/today').json()['new'] == []
    assert client.get('/v1/progress').json()['total_words'] == 0


def test_extra_is_free_alias_and_second_request_rejected(client):
    body = payload()
    assert client.post('/v1/today/extra', json=body).status_code == 200
    assert client.post('/v1/today/new', json=body).status_code == 200
    assert post(client).status_code == 409
    assert len(client.get('/v1/today/extra').json()['new']) == 10


def test_stale_review_source(client, clock):
    post(client)
    clock.today = date(2026, 8, 2)
    post(client, 11, 20, '2026-08-02')
    clock.today = date(2026, 8, 3)
    assert post(client, 1, 10, '2026-08-03', '2026-08-01').status_code == 409
