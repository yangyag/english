from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import get_today
from app.db import get_db
from app.schemas import ProgressOut
from app import study

router = APIRouter(tags=["progress"])


@router.get("/progress", response_model=ProgressOut)
def get_progress(db: Session = Depends(get_db), today: date = Depends(get_today)) -> ProgressOut:
    return ProgressOut.model_validate(study.progress_payload(db, today))
