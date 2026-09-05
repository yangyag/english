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


@pytest.mark.parametrize('ranks', [[2], [1, 3], list(range(2, 12)), [1] * 10])
def test_next_consecutive_words_required(client, ranks):
    body = payload()
    body['results'] = [dict(rank=r, known=True) for r in ranks]
    assert client.post('/v1/today/new', json=body).status_code == 409
    assert client.get('/v1/progress').json()['learned_count'] == 0


@pytest.mark.parametrize('known', [None, True, False])
def test_one_new_word_is_recorded_without_assessment(client, known):
    body = payload(1, 1, known=known)
    assert client.post('/v1/today/new', json=body).status_code == 200
    assert client.post('/v1/today/new', json=body).status_code == 200
    progress = client.get('/v1/progress').json()
    assert progress['learned_count'] == 1 and progress['next_rank'] == 2
    assert client.get('/v1/calendar?month=2026-08').json()['days'] == [
        dict(date='2026-08-01', new_count=1, review_count=0)]
    results = client.get('/v1/calendar/2026-08-01').json()['results']
    assert len(results) == 1 and results[0]['known'] is None
    assert post(client, 2, 4, known=None).status_code == 200
    assert client.get('/v1/progress').json()['next_rank'] == 5


def test_single_review_answers_resume_and_remain_available(client, clock):
    assert post(client, 1, 3, known=None).status_code == 200
    clock.today = date(2026, 8, 2)
    invalid = payload(1, 1, '2026-08-02', '2026-08-01', None)
    assert client.post('/v1/today/review', json=invalid).status_code == 400
    invalid['results'][0].pop('known')
    assert client.post('/v1/today/review', json=invalid).status_code == 400
    assert client.get('/v1/today').json()['review_completed'] == 0
    body = payload(1, 1, '2026-08-02', '2026-08-01', False)
    assert client.post('/v1/today/review', json=body).status_code == 200
    clock.today = date(2026, 8, 3)
    assert client.post('/v1/today/review', json=body).status_code == 200
    plan = client.get('/v1/today').json()
    assert plan['review_completed'] == 1 and plan['review'][0]['rank'] == 2
    assert post(client, 2, 2, '2026-08-03', '2026-08-01', True).status_code == 200
    assert client.get('/v1/calendar/2026-08-02').json()['results'][0]['known'] is False
    assert client.get('/v1/calendar/2026-08-03').json()['results'][0]['known'] is True
    assert client.get('/v1/progress').json()['learned_count'] == 3
    assert post(client, 4, 4, '2026-08-03', known=None).status_code == 200
    clock.today = date(2026, 8, 4)
    plan = client.get('/v1/today').json()
    assert plan['review_source_date'] == '2026-08-03'
    assert [w['rank'] for w in plan['review']] == [4]


def test_single_new_midnight_retry_and_stale_answer(client, clock):
    body = payload(1, 1, known=None)
    assert client.post('/v1/today/new', json=body).status_code == 200
    stale = payload(2, 2, known=None)
    clock.today = date(2026, 8, 2)
    assert client.post('/v1/today/new', json=body).status_code == 200
    assert client.post('/v1/today/new', json=stale).status_code == 409
    assert client.get('/v1/progress').json()['next_rank'] == 2
    assert client.get('/v1/calendar/2026-08-02').json()['results'] == []


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


def assert_counts(body, new, review):
    assert body['new_count'] == new
    assert body['review_count'] == review


def test_today_counts_accumulate_single_and_batched_saves(client):
    assert_counts(client.get('/v1/today').json(), 0, 0)
    for rank in (1, 2, 3):
        response = post(client, rank, rank, known=None)
        assert response.status_code == 200
        assert_counts(response.json(), rank, 0)
        assert_counts(client.get('/v1/today').json(), rank, 0)
    response = post(client, 4, 13, known=None)
    assert response.status_code == 200
    assert_counts(response.json(), 13, 0)
    response = client.post('/v1/today/extra', json=payload(14, 14, known=None))
    assert response.status_code == 200
    assert_counts(response.json(), 14, 0)
    assert_counts(client.get('/v1/today').json(), 14, 0)
    assert_counts(client.get('/v1/today/extra').json(), 14, 0)
    assert client.get('/v1/calendar?month=2026-08').json()['days'] == [
        dict(date='2026-08-01', new_count=14, review_count=0)]


def test_today_counts_split_new_and_review_and_ignore_previous_days(client, clock):
    assert post(client).status_code == 200
    clock.today = date(2026, 8, 2)
    assert_counts(client.get('/v1/today').json(), 0, 0)
    response = post(client, 11, 13, '2026-08-02', known=None)
    assert response.status_code == 200
    assert_counts(response.json(), 3, 0)
    response = post(client, 1, 1, '2026-08-02', '2026-08-01', False)
    assert response.status_code == 200
    assert_counts(response.json(), 3, 1)
    response = post(client, 2, 4, '2026-08-02', '2026-08-01', True)
    assert response.status_code == 200
    assert_counts(response.json(), 3, 4)
    assert_counts(client.get('/v1/today').json(), 3, 4)
    assert client.get('/v1/calendar?month=2026-08').json()['days'] == [
        dict(date='2026-08-01', new_count=10, review_count=0),
        dict(date='2026-08-02', new_count=3, review_count=4)]
    clock.today = date(2026, 8, 3)
    assert_counts(client.get('/v1/today').json(), 0, 0)
    response = post(client, 11, 11, '2026-08-03', '2026-08-02', False)
    assert response.status_code == 200
    assert_counts(response.json(), 0, 1)
    clock.today = date(2026, 8, 4)
    plan = client.get('/v1/today').json()
    assert_counts(plan, 0, 0)
    assert plan['review_completed'] == 1
    response = post(client, 12, 12, '2026-08-04', '2026-08-02', True)
    assert response.status_code == 200
    assert_counts(response.json(), 0, 1)
    assert response.json()['review_completed'] == 2


@pytest.mark.parametrize('kind', ['new', 'review'])
def test_today_counts_retry_returns_current_day_without_double_count(client, clock, kind):
    source = None
    if kind == 'review':
        assert post(client).status_code == 200
        source = '2026-08-01'
    clock.today = date(2026, 8, 2)
    path = '/v1/today/' + kind
    body = payload(1, 1, '2026-08-02', source)
    for _ in range(2):
        response = client.post(path, json=body)
        assert response.status_code == 200
        assert_counts(response.json(), int(kind == 'new'), int(kind == 'review'))
    assert post(client, 2, 2, '2026-08-02', source).status_code == 200
    response = client.post(path, json=body)
    assert response.status_code == 200
    assert_counts(response.json(), 2 * (kind == 'new'), 2 * (kind == 'review'))
    clock.today = date(2026, 8, 3)
    response = client.post(path, json=body)
    assert response.status_code == 200
    assert response.json()['date'] == '2026-08-03'
    assert_counts(response.json(), 0, 0)
    assert post(client, 3, 3, '2026-08-03', source).status_code == 200
    response = client.post(path, json=body)
    assert response.status_code == 200
    assert_counts(response.json(), int(kind == 'new'), int(kind == 'review'))
    body['results'][0]['known'] = False
    assert client.post(path, json=body).status_code == 409
    assert_counts(client.get('/v1/today').json(), int(kind == 'new'), int(kind == 'review'))
    days = client.get('/v1/calendar?month=2026-08').json()['days']
    assert_counts(days[-2], 2 * (kind == 'new'), 2 * (kind == 'review'))
    assert_counts(days[-1], int(kind == 'new'), int(kind == 'review'))


@pytest.mark.parametrize('kind,ranks,day,source,known,status', [
    ('new', [13], '2026-08-02', None, None, 409),
    ('new', [12, 12], '2026-08-02', None, None, 409),
    ('new', [11], '2026-08-02', None, None, 409),
    ('new', [12], '2026-08-01', None, None, 409),
    ('new', [12], '2026-08-02', '2026-08-01', None, 400),
    ('new', [], '2026-08-02', None, None, 422),
    ('new', list(range(12, 23)), '2026-08-02', None, None, 422),
    ('review', [2], '2026-08-02', '2026-08-01', None, 400),
    ('review', [2], '2026-08-02', '2026-07-31', True, 409),
    ('review', [2], '2026-08-01', '2026-08-01', True, 409),
    ('review', [3], '2026-08-02', '2026-08-01', False, 409),
])
def test_today_counts_do_not_increment_on_rejection(client, clock, kind, ranks, day, source, known, status):
    assert post(client).status_code == 200
    clock.today = date(2026, 8, 2)
    assert post(client, 11, 11, '2026-08-02', known=None).status_code == 200
    assert post(client, 1, 1, '2026-08-02', '2026-08-01', False).status_code == 200
    assert_counts(client.get('/v1/today').json(), 1, 1)
    body = payload(day=day, source=source, known=known)
    body['results'] = [dict(rank=rank, known=known) for rank in ranks]
    assert client.post('/v1/today/' + kind, json=body).status_code == status
    assert_counts(client.get('/v1/today').json(), 1, 1)
    assert_counts(client.get('/v1/calendar?month=2026-08').json()['days'][-1], 1, 1)
