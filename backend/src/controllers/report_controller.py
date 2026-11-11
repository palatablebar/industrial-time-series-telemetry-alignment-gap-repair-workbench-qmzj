"""Quality report + audit trail endpoints."""
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models import User
from src.services import audit_service, report_service


def summary(db: Session, user: User) -> dict:
    return report_service.summary(db, user, settings.DAILY_JOB_QUOTA)


def audit_recent(db: Session, limit: int = 30) -> dict:
    return {"items": audit_service.recent(db, limit)}
