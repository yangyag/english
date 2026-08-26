from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Phase = Literal["review", "new", "done"]


class WordOut(BaseModel):
    rank: int
    word: str
    meaning: str
    example: str
    example_ko: str

    model_config = {"from_attributes": True}


class TodayOut(BaseModel):
    date: date
    phase: Phase
    review: list[WordOut]
    new: list[WordOut]
    review_done: bool
    new_done: bool
    can_extra: bool = False


class WordResultIn(BaseModel):
    rank: int
    known: bool


class SubmitIn(BaseModel):
    results: list[WordResultIn] = Field(min_length=1)


class ProgressOut(BaseModel):
    total_words: int
    learned_count: int
    next_rank: int
    last_study_date: date | None
    streak_days: int
