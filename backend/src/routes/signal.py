from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import source_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import WRITE_ROLES, require_roles
from src.models import User
from src.schemas.source import SignalCreate

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def list_signals(
    device_code: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return source_controller.list_signals(db, device_code)


@router.post("")
def create_signal(
    payload: SignalCreate,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    return source_controller.create_signal(request, db, payload)
