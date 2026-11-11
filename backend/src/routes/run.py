from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import run_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import EXPORT_ROLES, require_roles
from src.models import User
from src.schemas.run import RunList

router = APIRouter(prefix="/alignment-runs", tags=["runs"])


@router.get("", response_model=RunList)
def list_runs(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return run_controller.list_runs(db)


@router.get("/{run_id}")
def run_detail(run_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return run_controller.run_detail(db, run_id)


@router.get("/{run_id}/export.csv")
def export_run(
    run_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*EXPORT_ROLES)),
):
    return run_controller.export_run_csv(request, db, run_id)
