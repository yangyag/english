from datetime import date

from fastapi.testclient import TestClient


def payload(start: int, end: int, known: bool = True) -> dict:
    return {"results": [{"rank": i, "known": known} for i in range(start, end + 1)]}


def test_first_day_is_new_only(client: TestClient) -> None:
    res = client.get("/v1/today")
    assert res.status_code == 200
    body = res.json()
    assert body["date"] == "2026-08-01"
    assert body["phase"] == "new"
    assert body["review"] == []
    assert body["review_done"] is False
    assert body["new_done"] is False
    assert [w["rank"] for w in body["new"]] == list(range(1, 11))
    assert body["new"][0]["word"] == "w1"
    assert body["new"][0]["meaning"] == "뜻1"
    assert body["new"][0]["example"] == "ex 1"
    assert body["new"][0]["example_ko"] == "예1"


def test_first_day_review_rejected(client: TestClient) -> None:
    res = client.post("/v1/today/review", json=payload(1, 10))
    assert res.status_code == 400
    assert "복습" in res.json()["detail"]


def test_first_day_new_completes(client: TestClient) -> None:
    res = client.post("/v1/today/new", json=payload(1, 10))
    assert res.status_code == 200
    body = res.json()
    assert body["phase"] == "done"
    assert body["new_done"] is True
    again = client.post("/v1/today/new", json=payload(1, 10))
    assert again.status_code == 409


def test_new_ranks_must_match(client: TestClient) -> None:
    res = client.post("/v1/today/new", json=payload(2, 11))
    assert res.status_code == 400


def test_review_is_gate_on_second_day(client: TestClient, clock) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    clock.today = date(2026, 8, 2)

    today = client.get("/v1/today").json()
    assert today["phase"] == "review"
    assert [w["rank"] for w in today["review"]] == list(range(1, 11))
    assert [w["rank"] for w in today["new"]] == list(range(11, 21))

    blocked = client.post("/v1/today/new", json=payload(11, 20))
    assert blocked.status_code == 409
    assert "복습" in blocked.json()["detail"]

    review = client.post("/v1/today/review", json=payload(1, 10, known=False))
    assert review.status_code == 200
    assert review.json()["phase"] == "new"
    assert review.json()["review_done"] is True

    second_review = client.post("/v1/today/review", json=payload(1, 10))
    assert second_review.status_code == 409

    learned = client.post("/v1/today/new", json=payload(11, 20))
    assert learned.status_code == 200
    assert learned.json()["phase"] == "done"


def test_extra_blocked_until_new_done(client: TestClient) -> None:
    blocked = client.get("/v1/today/extra")
    assert blocked.status_code == 409
    assert "신규" in blocked.json()["detail"]
    posted = client.post("/v1/today/extra", json=payload(1, 10))
    assert posted.status_code == 409


def test_extra_blocked_until_review_done(client: TestClient, clock) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    clock.today = date(2026, 8, 2)
    blocked = client.get("/v1/today/extra")
    assert blocked.status_code == 409
    assert "복습" in blocked.json()["detail"]


def test_extra_after_done_becomes_next_review(client: TestClient, clock) -> None:
    first = client.post("/v1/today/new", json=payload(1, 10))
    assert first.status_code == 200
    assert first.json()["phase"] == "done"
    assert first.json()["can_extra"] is True

    extra = client.get("/v1/today/extra")
    assert extra.status_code == 200
    body = extra.json()
    assert body["phase"] == "new"
    assert [w["rank"] for w in body["new"]] == list(range(11, 21))
    assert body["review"] == []

    submitted = client.post("/v1/today/extra", json=payload(11, 20))
    assert submitted.status_code == 200
    assert submitted.json()["phase"] == "done"
    assert submitted.json()["can_extra"] is True
    today = client.get("/v1/today").json()
    assert today["phase"] == "done"
    assert today["new_done"] is True

    clock.today = date(2026, 8, 2)
    nxt = client.get("/v1/today").json()
    assert nxt["phase"] == "review"
    assert [w["rank"] for w in nxt["review"]] == list(range(11, 21))
    assert [w["rank"] for w in nxt["new"]] == list(range(21, 31))


def test_extra_ranks_must_match(client: TestClient) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    res = client.post("/v1/today/extra", json=payload(12, 21))
    assert res.status_code == 400


def test_extra_stops_when_words_run_out(client: TestClient) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    assert client.post("/v1/today/extra", json=payload(11, 20)).status_code == 200
    assert client.post("/v1/today/extra", json=payload(21, 30)).status_code == 200
    empty = client.get("/v1/today/extra")
    assert empty.status_code == 400
    assert client.get("/v1/today").json()["can_extra"] is False


def test_skipped_day_still_reviews_last_batch(client: TestClient, clock) -> None:
    assert client.post("/v1/today/new", json=payload(1, 10)).status_code == 200
    clock.today = date(2026, 8, 5)
    today = client.get("/v1/today").json()
    assert today["phase"] == "review"
    assert [w["rank"] for w in today["review"]] == list(range(1, 11))
    assert [w["rank"] for w in today["new"]] == list(range(11, 21))
