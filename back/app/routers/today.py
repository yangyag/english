from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.schemas import SubmitIn, TodayOut
from app import study

router = APIRouter(tags=["today"])


@router.get("/today", response_model=TodayOut)
def get_today_plan(db: Session = Depends(get_db), today: date = Depends(get_today)) -> TodayOut:
    return study.today_payload(db, today)


@router.post("/today/review", response_model=TodayOut)
def post_today_review(
    body: SubmitIn,
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
) -> TodayOut:
    return study.submit_review(db, today, body)


@router.post("/today/new", response_model=TodayOut)
def post_today_new(
    body: SubmitIn,
    db: Session = Depends(get_db),
    today: date = Depends(get_today),
) -> TodayOut:
    return study.submit_new(db, today, body)
