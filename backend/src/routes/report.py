from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import report_controller
from src.middlewares.auth import get_current_user
from src.models import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return report_controller.summary(db, user)


@router.get("/audit")
def audit_recent(
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return report_controller.audit_recent(db, limit)
