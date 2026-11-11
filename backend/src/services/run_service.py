"""Run queries, aligned-series projections and CSV export."""
from __future__ import annotations

import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.error_codes import AppError, ErrorCode
from src.models import AlignmentRun, GapEvent, User
from src.utils.timeutil import from_epoch, iso

EXPORT_HEADER = [
    "signal_code",
    "device_code",
    "measure_name",
    "source_code",
    "unit",
    "timestamp",
    "value",
    "observed",
    "gap_filled",
]


def list_runs(db: Session) -> list[AlignmentRun]:
    return list(db.scalars(select(AlignmentRun).order_by(AlignmentRun.id.desc())))


def get_run(db: Session, run_id: int) -> AlignmentRun:
    run = db.get(AlignmentRun, run_id)
    if run is None:
        raise AppError(ErrorCode.NOT_FOUND, "对齐结果不存在", status_code=404)
    return run


def _creator_name(db: Session, run: AlignmentRun) -> str | None:
    job = run.job
    if job is None or not job.created_by:
        return None
    user = db.get(User, job.created_by)
    return user.display_name if user else None


def to_dict(db: Session, run: AlignmentRun) -> dict:
    job = run.job
    return {
        "id": run.id,
        "job_id": run.job_id,
        "job_name": job.name if job else "",
        "status": run.status,
        "started_at": iso(run.started_at),
        "finished_at": iso(run.finished_at),
        "duration_ms": run.duration_ms,
        "coverage_pct": run.coverage_pct,
        "drift_ms": run.drift_ms,
        "drift_confidence": run.drift_confidence,
        "anomaly_rate": run.anomaly_rate,
        "quality_score": run.quality_score,
        "gap_count": run.gap_count,
        "gap_total_s": run.gap_total_s,
        "point_count": run.point_count,
        "bucket_count": run.bucket_count,
        "failure_reason": run.failure_reason or "",
        "created_by_name": _creator_name(db, run),
    }


def to_detail(db: Session, run: AlignmentRun) -> dict:
    result = run.result_json or {}
    job = run.job
    gaps = list(
        db.scalars(select(GapEvent).where(GapEvent.run_id == run.id).order_by(GapEvent.start_ts, GapEvent.id))
    )
    gap_payload = []
    for gap in gaps:
        signal = gap.signal
        gap_payload.append(
            {
                "id": gap.id,
                "signal_code": signal.code if signal else "",
                "device_code": signal.device_code if signal else "",
                "measure_name": signal.measure_name if signal else "",
                "start_ts": iso(gap.start_ts),
                "end_ts": iso(gap.end_ts),
                "duration_s": gap.duration_s,
                "bucket_length": gap.bucket_length,
                "fill_strategy": gap.fill_strategy,
                "confidence": gap.confidence,
                "severity": gap.severity,
                "annotated": gap.annotated,
                "annotation": gap.annotation or "",
            }
        )
    t0 = float(result.get("t0") or 0.0)
    detail = to_dict(db, run)
    detail.update(
        {
            "t0": iso(from_epoch(t0)) if t0 else "",
            "grid_s": int(result.get("grid_s") or (job.grid_s if job else 5)),
            "window_start": iso(job.window_start) if job else "",
            "window_end": iso(job.window_end) if job else "",
            "agg_strategy": job.agg_strategy if job else "",
            "fill_strategy": job.fill_strategy if job else "",
            "drift": result.get("drift") or [],
            "series": result.get("series") or [],
            "gaps": gap_payload,
            "components": result.get("components") or {},
            "signal_coverage": [
                {
                    "signal_code": item.get("signal_code"),
                    "device_code": item.get("device_code"),
                    "measure_name": item.get("measure_name"),
                    "unit": item.get("unit"),
                    "source_code": item.get("source_code"),
                    "bucket_count": item.get("bucket_count"),
                    "observed_count": item.get("observed_count"),
                    "coverage": item.get("coverage"),
                }
                for item in (result.get("series") or [])
            ],
        }
    )
    return detail


def export_csv(db: Session, run_id: int) -> tuple[str, str, int]:
    run = get_run(db, run_id)
    if run.status != "completed":
        raise AppError(ErrorCode.JOB_FAILED, "只有成功完成的对齐结果可以导出", status_code=409)
    result = run.result_json or {}
    grid_s = int(result.get("grid_s") or 5)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_HEADER)
    row_count = 0
    for series in result.get("series") or []:
        values = series.get("values") or []
        observed = series.get("observed") or []
        for index, value in enumerate(values):
            is_observed = bool(observed[index]) if index < len(observed) else False
            series_start = float(series.get("start_ts") or result.get("t0") or 0.0)
            timestamp = iso(from_epoch(series_start + index * grid_s)) if series_start else ""
            writer.writerow(
                [
                    series.get("signal_code", ""),
                    series.get("device_code", ""),
                    series.get("measure_name", ""),
                    series.get("source_code", ""),
                    series.get("unit", ""),
                    timestamp,
                    "" if value is None else value,
                    "1" if is_observed else "0",
                    "0" if is_observed else "1",
                ]
            )
            row_count += 1
    job = run.job
    filename = f"tsalign-run-{run.id}-{job.name if job else 'aligned'}.csv".replace(" ", "_")
    return buffer.getvalue(), filename, row_count
