from fastapi import APIRouter
from sqlalchemy import text

from app.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, bool]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"ok": True}
