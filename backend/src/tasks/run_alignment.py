"""Celery task: execute one alignment job (the worker really runs both engines)."""
from src.config.celery_app import celery_app
from src.config.database import SessionLocal
from src.models import AlignmentJob
from src.services import alignment_service
from src.utils.logger import log_event


@celery_app.task(name="src.tasks.run_alignment.run_alignment_job", bind=True, max_retries=0)
def run_alignment_job(self, job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.get(AlignmentJob, job_id)
        if job is None:
            log_event("ALIGNMENT_JOB_MISSING", job_id=job_id)
            return {"ok": False, "reason": "job_not_found"}
        run = alignment_service.execute_job(db, job)
        return {
            "ok": run.status == "completed",
            "run_id": run.id,
            "status": run.status,
            "failure_reason": run.failure_reason,
        }
    except Exception as exc:  # pragma: no cover - surfaced through job status
        db.rollback()
        log_event("ALIGNMENT_TASK_ERROR", job_id=job_id, error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        db.close()
