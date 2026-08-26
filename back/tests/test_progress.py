from datetime import date

from fastapi.testclient import TestClient


def payload(start: int, end: int) -> dict:
    return {"results": [{"rank": i, "known": True} for i in range(start, end + 1)]}


def test_progress_starts_empty(client: TestClient) -> None:
    res = client.get("/v1/progress")
    assert res.status_code == 200
    body = res.json()
    assert body["total_words"] == 30
    assert body["learned_count"] == 0
    assert body["next_rank"] == 1
    assert body["last_study_date"] is None
    assert body["streak_days"] == 0


def test_progress_after_two_days(client: TestClient, clock) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    day1 = client.get("/v1/progress").json()
    assert day1["learned_count"] == 10
    assert day1["next_rank"] == 11
    assert day1["last_study_date"] == "2026-08-01"
    assert day1["streak_days"] == 1

    clock.today = date(2026, 8, 2)
    assert client.post("/v1/today/review", json=payload(1, 10)).status_code == 200
    assert client.post("/v1/today/new", json=payload(11, 20)).status_code == 200
    day2 = client.get("/v1/progress").json()
    assert day2["learned_count"] == 20
    assert day2["next_rank"] == 21
    assert day2["streak_days"] == 2


def test_streak_breaks_after_gap(client: TestClient, clock) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    clock.today = date(2026, 8, 4)
    body = client.get("/v1/progress").json()
    assert body["learned_count"] == 10
    assert body["streak_days"] == 0
    assert body["last_study_date"] == "2026-08-01"
