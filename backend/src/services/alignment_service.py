"""Execute one alignment job end-to-end: raw points -> align engine -> gap engine -> DB."""
from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.constants.enums import FailureReason, JobStatus, RunStatus
from src.models import AlignmentJob, AlignmentRun, GapEvent, RawTelemetry, Signal
from src.services import gap_engine
from src.services.align_engine import SignalInput, align_job
from src.utils.logger import log_event
from src.utils.timeutil import from_epoch, iso, to_epoch


def _load(inputs: list[Signal], db: Session, window_start: float, window_end: float) -> list[SignalInput]:
    payloads: list[SignalInput] = []
    for signal in inputs:
        rows = db.execute(
            select(RawTelemetry.ts, RawTelemetry.value, RawTelemetry.seq)
            .where(
                RawTelemetry.signal_id == signal.id,
                RawTelemetry.ts >= window_start,
                RawTelemetry.ts <= window_end,
            )
            .order_by(RawTelemetry.ts)
        ).all()
        payloads.append(
            SignalInput(
                signal_id=signal.id,
                signal_code=signal.code,
                device_code=signal.device_code,
                device_name=signal.device_name,
                measure_name=signal.measure_name,
                unit=signal.unit,
                source_id=signal.source_id,
                source_code=signal.source.code if signal.source else "",
                points=[(float(row[0]), float(row[1]), int(row[2])) for row in rows],
            )
        )
    return payloads


def execute_job(db: Session, job: AlignmentJob) -> AlignmentRun:
    started = time.perf_counter()
    signals = list(
        db.scalars(select(Signal).where(Signal.code.in_(job.signal_codes or [])).order_by(Signal.id))
    )
    window_start = to_epoch(job.window_start)
    window_end = to_epoch(job.window_end)
    run = db.scalar(select(AlignmentRun).where(AlignmentRun.job_id == job.id))
    if run is None:
        run = AlignmentRun(job_id=job.id, status=RunStatus.RUNNING.value)
        db.add(run)
    else:
        run.status = RunStatus.RUNNING.value
        run.failure_reason = ""
    job.status = JobStatus.RUNNING.value
    job.error_reason = ""
    db.commit()
    db.refresh(run)

    inputs = _load(signals, db, window_start, window_end)
    aligned = align_job(
        inputs,
        window_start=window_start,
        window_end=window_end,
        grid_s=int(job.grid_s),
        agg=job.agg_strategy,
    )
    result = aligned.to_dict()

    if aligned.failure:
        return _finalize_failure(db, job, run, aligned.failure, aligned.failure_detail, result, started)

    gaps = gap_engine.analyze(result, job.fill_strategy)
    if gaps.get("failure"):
        return _finalize_failure(db, job, run, gaps["failure"], {"reason": "对齐后无任何观测值"}, result, started)

    components = gaps["components"]
    drifts = result.get("drift") or []
    max_drift = max(drifts, key=lambda item: abs(item["drift_ms"]), default={"drift_ms": 0.0})
    result["components"] = components
    result["series"] = gaps["series"]
    result["gaps"] = gaps["gaps"]
    result["window_start"] = iso(job.window_start)
    result["window_end"] = iso(job.window_end)
    result["agg_strategy"] = job.agg_strategy
    result["fill_strategy"] = job.fill_strategy

    run.status = RunStatus.COMPLETED.value
    run.duration_ms = int((time.perf_counter() - started) * 1000)
    run.finished_at = datetime.now()
    run.coverage_pct = round(components["coverage"] * 100, 3)
    run.drift_ms = float(max_drift["drift_ms"])
    run.drift_confidence = float(result.get("drift_confidence") or 0.0)
    run.anomaly_rate = round(components["anomaly_rate"] * 100, 3)
    run.quality_score = float(components["quality_score"])
    run.gap_count = int(components["gap_count"])
    run.gap_total_s = float(components["gap_total_s"])
    run.point_count = int(result["point_count"])
    run.bucket_count = int(result["bucket_count"])
    run.failure_reason = ""
    run.result_json = result

    db.execute(delete(GapEvent).where(GapEvent.run_id == run.id))
    signal_by_code = {signal.code: signal for signal in signals}
    for gap in gaps["gaps"]:
        signal = signal_by_code.get(gap["signal_code"])
        if signal is None:
            continue
        db.add(
            GapEvent(
                run_id=run.id,
                signal_id=signal.id,
                start_ts=from_epoch(float(gap["start_ts"])),
                end_ts=from_epoch(float(gap["end_ts"])),
                duration_s=float(gap["duration_s"]),
                bucket_length=int(gap["bucket_length"]),
                fill_strategy=gap["fill_strategy"],
                confidence=float(gap["confidence"]),
                severity=gap["severity"],
            )
        )
    job.status = JobStatus.COMPLETED.value
    job.error_reason = ""
    db.commit()
    db.refresh(run)
    log_event(
        "ALIGNMENT_FINISHED",
        job_id=job.id,
        run_id=run.id,
        coverage=run.coverage_pct,
        drift_ms=run.drift_ms,
        quality=run.quality_score,
        gaps=run.gap_count,
    )
    return run


def _finalize_failure(
    db: Session,
    job: AlignmentJob,
    run: AlignmentRun,
    reason: str,
    detail: dict,
    result: dict,
    started: float,
) -> AlignmentRun:
    run.status = RunStatus.FAILED.value
    run.duration_ms = int((time.perf_counter() - started) * 1000)
    run.finished_at = datetime.now()
    run.failure_reason = reason
    run.result_json = {
        **result,
        "components": {},
        "series": [],
        "gaps": [],
        "failure_detail": detail,
    }
    job.status = JobStatus.FAILED.value
    job.error_reason = reason
    db.execute(delete(GapEvent).where(GapEvent.run_id == run.id))
    db.commit()
    db.refresh(run)
    log_event("ALIGNMENT_FAILED", job_id=job.id, run_id=run.id, reason=reason, detail=detail)
    return run
