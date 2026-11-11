"""Alignment job endpoints."""
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.middlewares.audit_logger import record
from src.middlewares.quota import consume_job_quota
from src.models import User
from src.services import job_service, signal_service
from src.utils.timeutil import parse_iso, to_epoch


def create_job(request, db: Session, payload, user: User) -> dict:
    quota = consume_job_quota(db, user)
    job = job_service.create_job(db, payload, user)
    record(
        request,
        "alignment_job.create",
        "alignment_job",
        job.id,
        after={"name": job.name, "grid_s": job.grid_s, "device_codes": job.device_codes},
    )
    return {"job": job_service.to_dict(db, job), "quota": quota}


def list_jobs(db: Session) -> dict:
    return {"items": [job_service.to_dict(db, job) for job in job_service.list_jobs(db)]}


def job_detail(db: Session, job_id: int) -> dict:
    job = job_service.get_job(db, job_id)
    run = job_service.run_of(db, job_id)
    return {"job": job_service.to_dict(db, job), "run_id": run.id if run else None}


def run_job(request, db: Session, job_id: int, user: User) -> dict:
    job = job_service.rerun(db, job_id)
    record(request, "alignment_job.run", "alignment_job", job.id)
    return {"job": job_service.to_dict(db, job)}


def estimate(db: Session, payload) -> dict:
    signals = signal_service.signals_for_devices(db, payload.device_codes)
    window_start = to_epoch(parse_iso(payload.window_start))
    window_end = to_epoch(parse_iso(payload.window_end))
    grid_s = int(payload.grid_s)
    span = max(1, int(round(window_end - window_start)))
    points = signal_service.point_count(db, [signal.id for signal in signals], window_start, window_end)
    return {
        "bucket_count": span // grid_s,
        "point_count": points,
        "signal_count": len(signals),
        "span_seconds": span,
        "grid_s": grid_s,
    }


def quota_state(user: User) -> dict:
    return {
        "daily_quota": settings.DAILY_JOB_QUOTA,
        "quota_used": int(user.quota_used or 0),
        "quota_remaining": max(0, settings.DAILY_JOB_QUOTA - int(user.quota_used or 0)),
    }
