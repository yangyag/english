from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app import study
from app.db import get_db

router = APIRouter(tags=["calendar"])


@router.get("/calendar")
def get_calendar(month: str = Query(pattern=r"^\d{4}-\d{2}$"), db: Session = Depends(get_db)):
    try:
        start = date.fromisoformat(month + "-01")
        if start.year >= 9999:
            raise ValueError()
    except ValueError:
        raise HTTPException(422, "올바른 월을 지정해 주세요.")
    return study.calendar_payload(db, start)


@router.get("/calendar/{day}")
def get_day(day: date, db: Session = Depends(get_db)):
    return study.day_payload(db, day)
