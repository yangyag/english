from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field


class WordOut(BaseModel):
    rank: int
    word: str
    meaning: str
    example: str
    example_ko: str
    model_config = {"from_attributes": True}


class TodayOut(BaseModel):
    date: date
    new: list[WordOut]
    review: list[WordOut]
    review_source_date: date | None
    review_total: int
    review_completed: int


class WordResultIn(BaseModel):
    rank: int = Field(gt=0)
    known: bool | None = None


class SubmitIn(BaseModel):
    request_id: UUID
    study_date: date
    source_date: date | None = None
    results: list[WordResultIn] = Field(min_length=1, max_length=10)


class ProgressOut(BaseModel):
    total_words: int
    learned_count: int
    next_rank: int
    last_study_date: date | None
    study_days: int
    undated_learned_count: int
