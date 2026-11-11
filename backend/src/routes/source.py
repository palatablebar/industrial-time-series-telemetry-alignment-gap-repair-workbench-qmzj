from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import source_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import WRITE_ROLES, require_roles
from src.models import User
from src.schemas.source import (
    SignalCreate,
    SourceCreate,
    SourceDetail,
    SourceList,
    SourceUpdate,
)

router = APIRouter(prefix="/data-sources", tags=["sources"])


@router.get("", response_model=SourceList)
def list_sources(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return source_controller.list_sources(db)


@router.get("/{source_id}", response_model=SourceDetail)
def source_detail(
    source_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> dict:
    return source_controller.source_detail(db, source_id)


@router.post("")
def create_source(
    payload: SourceCreate,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    return source_controller.create_source(request, db, payload)


@router.patch("/{source_id}")
def update_source(
    source_id: int,
    payload: SourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    return source_controller.update_source(request, db, source_id, payload)
