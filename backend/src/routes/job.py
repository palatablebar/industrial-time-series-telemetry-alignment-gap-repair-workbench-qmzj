from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import job_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import ENGINEER, WRITE_ROLES, require_roles
from src.models import User
from src.schemas.job import EstimateRequest, EstimateResponse, JobCreate, JobList

router = APIRouter(prefix="/alignment-jobs", tags=["jobs"])


@router.get("", response_model=JobList)
def list_jobs(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return job_controller.list_jobs(db)


@router.post("")
def create_job(
    payload: JobCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
) -> dict:
    return job_controller.create_job(request, db, payload, user)


@router.get("/{job_id}")
def job_detail(job_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return job_controller.job_detail(db, job_id)


@router.post("/{job_id}/run")
def run_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(ENGINEER)),
) -> dict:
    return job_controller.run_job(request, db, job_id, user)


@router.post("/estimate", response_model=EstimateResponse)
def estimate(
    payload: EstimateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    return job_controller.estimate(db, payload)
