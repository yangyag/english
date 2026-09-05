from datetime import date, datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.migration import lock_study
from app.models import BatchResult, StudyBatch, StudyState, Word
from app.schemas import SubmitIn, TodayOut, WordOut

KST = ZoneInfo("Asia/Seoul")
BATCH_SIZE = 10


def _next_rank(db: Session) -> int:
    state = db.get(StudyState, 1)
    return state.next_rank if state else 1


def _new_words(db: Session) -> list[Word]:
    return list(db.scalars(select(Word).where(Word.rank >= _next_rank(db)).order_by(Word.rank).limit(BATCH_SIZE)))


def _review(db: Session, today: date):
    source = db.scalar(select(func.max(StudyBatch.study_date)).where(StudyBatch.kind == "new", StudyBatch.study_date < today))
    if source is None:
        return None, [], []
    ranks = list(db.scalars(select(BatchResult.rank).join(StudyBatch).where(
        StudyBatch.kind == "new", StudyBatch.study_date == source).distinct().order_by(BatchResult.rank)))
    completed = set(db.scalars(select(BatchResult.rank).join(StudyBatch).where(
        StudyBatch.kind == "review", StudyBatch.source_date == source)))
    return source, ranks, [rank for rank in ranks if rank not in completed]


def today_payload(db: Session, today: date) -> TodayOut:
    source, ranks, remaining = _review(db, today)
    words = db.scalars(select(Word).where(Word.rank.in_(remaining[:BATCH_SIZE])).order_by(Word.rank))
    return TodayOut(date=today, new=[WordOut.model_validate(w) for w in _new_words(db)],
                    review=[WordOut.model_validate(w) for w in words], review_source_date=source,
                    review_total=len(ranks), review_completed=len(ranks) - len(remaining))


def submit(db: Session, today: date, body: SubmitIn, kind: str) -> TodayOut:
    lock_study(db)
    db.expire_all()
    fingerprint = kind + ':' + body.model_dump_json(exclude={"request_id"})
    prior = db.scalar(select(StudyBatch).where(StudyBatch.request_id == str(body.request_id)))
    if prior:
        if prior.fingerprint != fingerprint:
            raise HTTPException(409, "같은 요청 번호로 다른 결과를 제출할 수 없습니다.")
        return today_payload(db, today)
    if body.study_date != today:
        raise HTTPException(409, "날짜가 바뀌었습니다. 오늘 학습을 다시 열어 주세요.")
    if kind == "new":
        if body.source_date is not None:
            raise HTTPException(400, "신규 학습에는 복습 날짜를 지정하지 않습니다.")
        expected = [word.rank for word in _new_words(db)]
    else:
        if any(item.known is None for item in body.results):
            raise HTTPException(400, "복습에는 기억 여부가 필요합니다.")
        source, _, remaining = _review(db, today)
        if source is None or source != body.source_date:
            raise HTTPException(409, "복습 대상이 바뀌었습니다. 학습을 다시 열어 주세요.")
        expected = remaining[:BATCH_SIZE]
    if not expected:
        raise HTTPException(409, "제출할 단어가 없습니다. 기록을 확인해 주세요.")
    # Accept the next consecutive prefix; old clients may still send ten.
    submitted = sorted(item.rank for item in body.results)
    if submitted != expected[:len(submitted)]:
        raise HTTPException(409, "학습 목록이 바뀌었거나 순서가 맞지 않습니다. 학습을 다시 열어 주세요.")
    batch = StudyBatch(request_id=str(body.request_id), fingerprint=fingerprint, study_date=today,
                       kind=kind, source_date=body.source_date, completed_at=datetime.now(KST))
    db.add(batch)
    db.flush()
    db.add_all([BatchResult(batch_id=batch.id, rank=r.rank, known=r.known if kind == "review" else None)
                for r in body.results])
    if kind == "new":
        state = db.get(StudyState, 1)
        if state is None:
            state = StudyState(id=1)
            db.add(state)
        state.next_rank = submitted[-1] + 1
        state.last_study_date = today
    db.flush()
    return today_payload(db, today)


def progress_payload(db: Session, today: date) -> dict:
    recorded = select(BatchResult.rank).join(StudyBatch).where(StudyBatch.kind == "new")
    learned = db.scalar(select(func.count()).select_from(Word).where(
        (Word.rank < _next_rank(db)) | Word.rank.in_(recorded))) or 0
    dated = db.scalar(select(func.count(func.distinct(BatchResult.rank))).select_from(BatchResult).join(StudyBatch)
                      .where(StudyBatch.kind == "new")) or 0
    return dict(total_words=db.scalar(select(func.count()).select_from(Word)) or 0,
                learned_count=learned, next_rank=_next_rank(db),
                last_study_date=db.scalar(select(func.max(StudyBatch.study_date))),
                study_days=db.scalar(select(func.count(func.distinct(StudyBatch.study_date)))) or 0,
                undated_learned_count=max(0, learned - dated))


def calendar_payload(db: Session, month: date) -> dict:
    end = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    rows = db.execute(select(StudyBatch.study_date, StudyBatch.kind, func.count(BatchResult.id))
                      .join(BatchResult).where(StudyBatch.study_date >= month, StudyBatch.study_date < end)
                      .group_by(StudyBatch.study_date, StudyBatch.kind).order_by(StudyBatch.study_date))
    days = {}
    for day, kind, count in rows:
        days.setdefault(day, {"date": day, "new_count": 0, "review_count": 0})[kind + "_count"] = count
    return {"month": month.strftime("%Y-%m"), "days": list(days.values())}


def day_payload(db: Session, day: date) -> dict:
    rows = db.execute(select(Word, StudyBatch.kind, BatchResult.known).join(
        BatchResult, Word.rank == BatchResult.rank).join(StudyBatch)
        .where(StudyBatch.study_date == day).order_by(StudyBatch.id, Word.rank))
    return {"date": day, "results": [dict(**WordOut.model_validate(w).model_dump(), kind=k, known=v)
                                      for w, k, v in rows]}
