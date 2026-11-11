from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import gap_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import ANNOTATE_ROLES, require_roles
from src.models import User
from src.schemas.gap import GapAnnotation

router = APIRouter(prefix="/gap-events", tags=["gaps"])


@router.get("")
def list_gaps(
    run_id: int | None = Query(default=None),
    severity: str | None = Query(default=None),
    device_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return gap_controller.list_gaps(db, run_id=run_id, severity=severity, device_code=device_code)


@router.patch("/{gap_id}/annotate")
def annotate_gap(
    gap_id: int,
    payload: GapAnnotation,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*ANNOTATE_ROLES)),
) -> dict:
    return gap_controller.annotate_gap(request, db, gap_id, payload)
