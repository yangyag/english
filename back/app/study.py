from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import StudySession, StudyState, Word, WordResult
from app.schemas import Phase, SubmitIn, TodayOut, WordOut

KST = ZoneInfo("Asia/Seoul")
STATE_ID = 1


def _now() -> datetime:
    return datetime.now(KST)


def _state(db: Session) -> StudyState:
    row = db.get(StudyState, STATE_ID)
    if row is None:
        row = StudyState(id=STATE_ID, next_rank=1, last_study_date=None)
        db.add(row)
        db.flush()
    return row


def _max_rank(db: Session) -> int:
    return db.scalar(select(func.max(Word.rank))) or 0


def _words(db: Session, start: int | None, end: int | None) -> list[Word]:
    if start is None or end is None or start > end:
        return []
    return list(
        db.scalars(select(Word).where(Word.rank.between(start, end)).order_by(Word.rank))
    )


def _phase(session: StudySession) -> Phase:
    if session.new_done_at is not None:
        return "done"
    if session.review_from_rank is not None and session.review_done_at is None:
        return "review"
    return "new"


def _range_for_new(next_rank: int, batch: int, max_rank: int) -> tuple[int | None, int | None]:
    if max_rank < 1 or next_rank > max_rank:
        return None, None
    return next_rank, min(next_rank + batch - 1, max_rank)


def get_or_create_session(db: Session, today: date) -> StudySession:
    row = db.scalar(select(StudySession).where(StudySession.study_date == today))
    if row is not None:
        return row

    settings = get_settings()
    state = _state(db)
    max_rank = _max_rank(db)
    new_from, new_to = _range_for_new(state.next_rank, settings.batch_size, max_rank)
    review_from = review_to = None
    if state.next_rank > 1:
        review_to = state.next_rank - 1
        review_from = max(1, review_to - settings.batch_size + 1)

    row = StudySession(
        study_date=today,
        review_from_rank=review_from,
        review_to_rank=review_to,
        new_from_rank=new_from,
        new_to_rank=new_to,
    )
    db.add(row)
    db.flush()
    return row


def today_payload(db: Session, today: date) -> TodayOut:
    session = get_or_create_session(db, today)
    review = _words(db, session.review_from_rank, session.review_to_rank)
    new = _words(db, session.new_from_rank, session.new_to_rank)
    phase = _phase(session)
    if not review and not new:
        phase = "done"
    return TodayOut(
        date=today,
        phase=phase,
        review=[WordOut.model_validate(w) for w in review],
        new=[WordOut.model_validate(w) for w in new],
        review_done=session.review_done_at is not None,
        new_done=session.new_done_at is not None,
    )


def _expected_ranks(db: Session, session: StudySession, kind: str) -> list[int]:
    if kind == "review":
        start, end = session.review_from_rank, session.review_to_rank
    else:
        start, end = session.new_from_rank, session.new_to_rank
    return [w.rank for w in _words(db, start, end)]


def _save_results(db: Session, session: StudySession, kind: str, body: SubmitIn) -> int:
    expected = _expected_ranks(db, session, kind)
    if not expected:
        raise HTTPException(status_code=400, detail="오늘 제출할 단어가 없습니다.")
    got = [item.rank for item in body.results]
    if sorted(got) != expected:
        raise HTTPException(
            status_code=400,
            detail=f"제출 순위가 오늘 {kind} 목록과 다릅니다.",
        )
    now = _now()
    for item in body.results:
        db.add(
            WordResult(
                session_id=session.id,
                rank=item.rank,
                kind=kind,
                known=item.known,
                studied_at=now,
            )
        )
    return len(body.results)


def submit_review(db: Session, today: date, body: SubmitIn) -> TodayOut:
    session = get_or_create_session(db, today)
    if session.review_from_rank is None:
        raise HTTPException(status_code=400, detail="오늘 복습할 단어가 없습니다.")
    if session.review_done_at is not None:
        raise HTTPException(status_code=409, detail="오늘 복습은 이미 완료했습니다.")
    _save_results(db, session, "review", body)
    session.review_done_at = _now()
    db.flush()
    return today_payload(db, today)


def submit_new(db: Session, today: date, body: SubmitIn) -> TodayOut:
    session = get_or_create_session(db, today)
    if session.review_from_rank is not None and session.review_done_at is None:
        raise HTTPException(status_code=409, detail="복습을 먼저 완료하세요.")
    if session.new_from_rank is None:
        raise HTTPException(status_code=400, detail="오늘 배울 새 단어가 없습니다.")
    if session.new_done_at is not None:
        raise HTTPException(status_code=409, detail="오늘 신규 학습은 이미 완료했습니다.")
    _save_results(db, session, "new", body)
    session.new_done_at = _now()
    state = _state(db)
    state.next_rank = session.new_to_rank + 1
    state.last_study_date = today
    db.flush()
    return today_payload(db, today)


def progress_payload(db: Session, today: date) -> dict:
    state = _state(db)
    total = db.scalar(select(func.count()).select_from(Word)) or 0
    learned = max(0, state.next_rank - 1)
    streak = 0
    cursor = today
    if state.last_study_date is not None:
        if state.last_study_date == today or state.last_study_date == today - timedelta(days=1):
            cursor = state.last_study_date
            while True:
                row = db.scalar(
                    select(StudySession).where(
                        StudySession.study_date == cursor,
                        StudySession.new_done_at.is_not(None),
                    )
                )
                if row is None:
                    break
                streak += 1
                cursor = cursor - timedelta(days=1)
    return {
        "total_words": total,
        "learned_count": learned,
        "next_rank": state.next_rank,
        "last_study_date": state.last_study_date,
        "streak_days": streak,
    }
