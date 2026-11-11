import time

from fastapi import APIRouter
from sqlalchemy import text

from src.config.database import SessionLocal
from src.middlewares.quota import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    database = "ok"
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - infra probe
        database = f"error: {type(exc).__name__}"
    finally:
        db.close()
    return {
        "status": "ok",
        "service": "tsalign-backend",
        "database": database,
        "redis": "ok" if get_redis() is not None else "degraded",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
