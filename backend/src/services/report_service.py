"""Quality report aggregates for the /reports page (computed from stored runs)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import JobStatus, RunStatus
from src.constants.messages import CUSTOMER
from src.models import AlignmentJob, AlignmentRun, GapEvent, User
from src.services import auth_service, run_service
from src.services.gap_engine import QUALITY_FORMULA
from src.utils.timeutil import iso, now_local


def summary(db: Session, user: User, daily_limit: int) -> dict:
    runs = list(db.scalars(select(AlignmentRun).order_by(AlignmentRun.id.desc())))
    completed = [run for run in runs if run.status == RunStatus.COMPLETED.value]
    quality_values = [run.quality_score for run in completed if run.quality_score]
    coverage_values = [run.coverage_pct for run in completed if run.coverage_pct]
    gap_total = int(db.scalar(select(func.count(GapEvent.id))) or 0)
    severity_rows = db.execute(
        select(GapEvent.severity, func.count(GapEvent.id)).group_by(GapEvent.severity)
    ).all()
    severity_map = {str(row[0]): int(row[1]) for row in severity_rows}
    drift_table = []
    for run in completed[:8]:
        result = run.result_json or {}
        for item in result.get("drift") or []:
            drift_table.append(
                {
                    "run_id": run.id,
                    "job_name": run.job.name if run.job else "",
                    "source_code": item.get("source_code", ""),
                    "drift_ms": item.get("drift_ms", 0),
                    "confidence": item.get("confidence", 0),
                }
            )
    trend = [
        {
            "run_id": run.id,
            "job_name": run.job.name if run.job else "",
            "quality_score": run.quality_score,
            "coverage_pct": run.coverage_pct,
            "finished_at": iso(run.finished_at),
        }
        for run in reversed(completed[:10])
    ]
    return {
        "customer": CUSTOMER,
        "generated_at": iso(now_local()),
        "run_count": len(runs),
        "completed_runs": len(completed),
        "average_quality": round(sum(quality_values) / len(quality_values), 2) if quality_values else 0.0,
        "best_coverage": round(max(coverage_values), 3) if coverage_values else 0.0,
        "total_gaps": gap_total,
        "formula": QUALITY_FORMULA,
        "quality_trend": trend,
        "drift_table": drift_table,
        "gap_severity": [
            {"severity": "high", "count": severity_map.get("high", 0)},
            {"severity": "medium", "count": severity_map.get("medium", 0)},
            {"severity": "low", "count": severity_map.get("low", 0)},
        ],
        "recent_runs": [run_service.to_dict(db, run) for run in runs[:6]],
        "quota": auth_service.quota_snapshot(user, daily_limit),
        "job_status_counts": {
            str(row[0]): int(row[1])
            for row in db.execute(
                select(AlignmentRun.status, func.count(AlignmentRun.id)).group_by(AlignmentRun.status)
            ).all()
        },
        "pending_jobs": int(
            db.scalar(
                select(func.count(AlignmentJob.id)).where(AlignmentJob.status == JobStatus.PENDING.value)
            )
            or 0
        ),
    }
