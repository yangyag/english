from datetime import date
from test_today import post


def test_progress_and_calendar(client, clock):
    initial = client.get('/v1/progress').json()
    assert initial['learned_count'] == initial['study_days'] == 0
    assert initial['last_study_date'] is None
    post(client)
    post(client, 11, 20)
    clock.today = date(2026, 9, 1)
    post(client, 1, 10, '2026-09-01', '2026-08-01', False)
    progress = client.get('/v1/progress').json()
    assert progress['learned_count'] == 20
    assert progress['study_days'] == 2
    assert progress['last_study_date'] == '2026-09-01'
    assert client.get('/v1/calendar?month=2026-08').json()['days'] == [dict(date='2026-08-01', new_count=20, review_count=0)]
    assert client.get('/v1/calendar?month=2026-09').json()['days'] == [dict(date='2026-09-01', new_count=0, review_count=10)]
    results = client.get('/v1/calendar/2026-09-01').json()['results']
    assert len(results) == 10 and all(r['kind'] == 'review' and not r['known'] for r in results)
    assert client.get('/v1/calendar/2026-09-02').json()['results'] == []


def test_month_validation_and_year_boundary(client, clock):
    for month in ['bad', '2026-13', '9999-12', '0000-01']:
        assert client.get('/v1/calendar', params={'month': month}).status_code == 422
    clock.today = date(2026, 12, 31)
    post(client, day='2026-12-31')
    assert len(client.get('/v1/calendar?month=2026-12').json()['days']) == 1
    assert client.get('/v1/calendar?month=2027-01').json()['days'] == []
