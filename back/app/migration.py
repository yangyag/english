"""Additive, repeatable legacy import. Never modify the legacy ledger or cursor."""
from collections import defaultdict
from zoneinfo import ZoneInfo
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.models import BatchResult, StudyBatch, WordResult

KST = ZoneInfo("Asia/Seoul")


def lock_study(db: Session) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(714205, 1)"))


def migrate_legacy(db: Session) -> int:
    lock_study(db)
    groups = defaultdict(list)
    for row in db.scalars(select(WordResult).order_by(WordResult.id)):
        stamp = row.studied_at
        if stamp.tzinfo is None:
            raise ValueError("Legacy studied_at must include its timezone")
        groups[(row.session_id, row.kind, stamp.astimezone(KST).date())].append(row)
    imported = 0
    for (session_id, kind, day), rows in groups.items():
        key = f"legacy:{session_id}:{kind}:{day}"
        batch = db.scalar(select(StudyBatch).where(StudyBatch.request_id == key))
        if batch is None:
            batch = StudyBatch(request_id=key, fingerprint="legacy", study_date=day,
                               kind=kind, source_date=None, completed_at=max(row.studied_at for row in rows))
            db.add(batch)
            db.flush()
        existing = set(db.scalars(select(BatchResult.rank).where(BatchResult.batch_id == batch.id)))
        missing = [row for row in rows if row.rank not in existing]
        if missing:
            batch.completed_at = max(row.studied_at for row in rows)
            db.add_all([BatchResult(batch_id=batch.id, rank=r.rank, known=r.known) for r in missing])
            imported += len(missing)
    db.flush()
    return imported
