from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings

SCHEMA = get_settings().pgschema


class Base(DeclarativeBase):
    pass


class Word(Base):
    __tablename__ = "word"
    __table_args__ = {"schema": SCHEMA}

    rank: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(Text, nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str] = mapped_column(Text, nullable=False)
    example_ko: Mapped[str] = mapped_column(Text, nullable=False)


class StudyState(Base):
    __tablename__ = "study_state"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_study_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class StudySession(Base):
    __tablename__ = "study_session"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    review_from_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_to_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_from_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_to_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    new_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[list["WordResult"]] = relationship(back_populates="session")


class WordResult(Base):
    __tablename__ = "word_result"
    __table_args__ = (
        UniqueConstraint("session_id", "rank", "kind", name="uq_word_result_session_rank_kind"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.study_session.id"), nullable=False)
    rank: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.word.rank"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    known: Mapped[bool] = mapped_column(Boolean, nullable=False)
    studied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session: Mapped[StudySession] = relationship(back_populates="results")


class StudyBatch(Base):
    __tablename__ = "study_batch"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(100), unique=True)
    fingerprint: Mapped[str] = mapped_column(Text)
    study_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(16))
    source_date: Mapped[date | None] = mapped_column(Date, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BatchResult(Base):
    __tablename__ = "batch_result"
    __table_args__ = (UniqueConstraint("batch_id", "rank", name="uq_batch_result_rank"), {"schema": SCHEMA})
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.study_batch.id"), index=True)
    rank: Mapped[int] = mapped_column(ForeignKey(f"{SCHEMA}.word.rank"), index=True)
    known: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
