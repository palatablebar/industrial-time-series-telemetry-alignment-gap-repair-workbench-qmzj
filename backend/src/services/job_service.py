"""Alignment job creation, listing and Celery dispatch."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.celery_app import celery_app
from src.constants.enums import AggStrategy, FillStrategy, GridSize, JobStatus
from src.constants.error_codes import AppError, ErrorCode
from src.models import AlignmentJob, AlignmentRun, User
from src.services import signal_service
from src.utils.logger import log_event
from src.utils.timeutil import iso, parse_iso

TASK_NAME = "src.tasks.run_alignment.run_alignment_job"


def _validate(job_payload) -> None:
    if int(job_payload.grid_s) not in tuple(GridSize.values()):
        raise AppError(ErrorCode.VALIDATION_FAILED, "目标网格只能是 1 / 5 / 60 秒", status_code=422)
    if job_payload.agg_strategy not in tuple(item.value for item in AggStrategy):
        raise AppError(ErrorCode.VALIDATION_FAILED, "聚合策略不合法", status_code=422)
    if job_payload.fill_strategy not in tuple(item.value for item in FillStrategy):
        raise AppError(ErrorCode.VALIDATION_FAILED, "填补策略不合法", status_code=422)


def _default_name(device_codes: list[str], window_start: datetime) -> str:
    stamp = window_start.strftime("%m%d-%H%M%S")
    devices = "+".join(device_codes[:3])
    return f"{devices}-对齐-{stamp}"


def create_job(db: Session, payload, user: User) -> AlignmentJob:
    _validate(payload)
    try:
        window_start = parse_iso(payload.window_start)
        window_end = parse_iso(payload.window_end)
    except (ValueError, TypeError) as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, "时间窗格式不合法", status_code=422) from exc
    if window_end <= window_start:
        raise AppError(ErrorCode.VALIDATION_FAILED, "结束时间必须晚于开始时间", status_code=422)
    signals = signal_service.signals_for_devices(db, payload.device_codes)
    name = (payload.name or "").strip() or _default_name(payload.device_codes, window_start)
    existing = db.scalar(select(AlignmentJob).where(AlignmentJob.name == name))
    if existing is not None:
        raise AppError(ErrorCode.CONFLICT, "同名对齐任务已存在，请更换名称", status_code=409)
    params = {
        "device_codes": payload.device_codes,
        "signal_codes": [signal.code for signal in signals],
        "window_start": iso(window_start),
        "window_end": iso(window_end),
        "grid_s": int(payload.grid_s),
        "agg_strategy": payload.agg_strategy,
        "fill_strategy": payload.fill_strategy,
    }
    job = AlignmentJob(
        name=name,
        device_codes=payload.device_codes,
        signal_codes=[signal.code for signal in signals],
        window_start=window_start,
        window_end=window_end,
        grid_s=int(payload.grid_s),
        agg_strategy=payload.agg_strategy,
        fill_strategy=payload.fill_strategy,
        status=JobStatus.PENDING.value,
        params_snapshot=params,
        note=payload.note or "",
        created_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    dispatch(db, job)
    return job


def dispatch(db: Session, job: AlignmentJob) -> bool:
    job.status = JobStatus.PENDING.value
    db.commit()
    try:
        celery_app.send_task(TASK_NAME, args=[job.id])
        return True
    except Exception as exc:  # broker problems must not hide the created job
        log_event("ALIGNMENT_DISPATCH_FAILED", job_id=job.id, error=f"{type(exc).__name__}: {exc}")
        return False


def list_jobs(db: Session) -> list[AlignmentJob]:
    return list(db.scalars(select(AlignmentJob).order_by(AlignmentJob.id.desc())))


def get_job(db: Session, job_id: int) -> AlignmentJob:
    job = db.get(AlignmentJob, job_id)
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, "对齐任务不存在", status_code=404)
    return job


def rerun(db: Session, job_id: int) -> AlignmentJob:
    job = get_job(db, job_id)
    if job.status == JobStatus.RUNNING.value:
        raise AppError(ErrorCode.JOB_NOT_RUNNABLE, "任务正在运行中", status_code=409)
    dispatch(db, job)
    return job


def run_of(db: Session, job_id: int) -> AlignmentRun | None:
    return db.scalar(select(AlignmentRun).where(AlignmentRun.job_id == job_id))


def to_dict(db: Session, job: AlignmentJob) -> dict:
    creator = db.get(User, job.created_by) if job.created_by else None
    run = run_of(db, job.id)
    return {
        "id": job.id,
        "name": job.name,
        "device_codes": job.device_codes or [],
        "signal_codes": job.signal_codes or [],
        "window_start": iso(job.window_start),
        "window_end": iso(job.window_end),
        "grid_s": job.grid_s,
        "agg_strategy": job.agg_strategy,
        "fill_strategy": job.fill_strategy,
        "status": job.status,
        "error_reason": job.error_reason or "",
        "note": job.note or "",
        "created_by_name": creator.display_name if creator else None,
        "run_id": run.id if run else None,
        "quality_score": run.quality_score if run else None,
        "created_at": iso(job.created_at),
    }
