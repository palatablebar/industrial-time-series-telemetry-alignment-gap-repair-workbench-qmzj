"""Idempotent demo seed for TSALIGN (瀚川重工 · 设备可靠性组).

Generates deterministic synthetic gateway exports (12 signals / 5,760 raw samples),
then really runs the two Python engines for the seeded jobs so the demo numbers are
computed, not hard-coded. Repeat runs upsert by natural keys and keep user gap
annotations; the final line is always exactly one ``SEED_SUMMARY ...`` line.
"""
from __future__ import annotations

import math
import sys
from datetime import datetime

import numpy as np

from src.config.database import SessionLocal, init_db
from src.constants.enums import JobStatus, RunStatus
from src.constants.messages import DEMO_PASSWORD
from src.models import AlignmentJob, AlignmentRun, DataSource, GapEvent, RawTelemetry, Signal, User
from src.services.demo_data import (
    BASE_DATETIME,
    BASE_EPOCH,
    CYCLE_S,
    DEFAULT_PASSWORD,
    POINTS_PER_SIGNAL,
    SEED_JOBS,
    SEED_SIGNALS,
    SEED_SOURCES,
    build_seed_series,
    compute_seed_results,
)
from src.utils.logger import log_event
from src.utils.password import hash_password
from src.utils.timeutil import from_epoch, iso, to_epoch

SEED_EMAILS = ["engineer@tsalign.demo", "analyst@tsalign.demo", "viewer@tsalign.demo"]

SEED_USERS = [
    {
        "email": "engineer@tsalign.demo",
        "display_name": "周砚舟",
        "role": "engineer",
        "unit": "设备可靠性组 · 数据工程",
        "daily_job_quota": 40,
    },
    {
        "email": "analyst@tsalign.demo",
        "display_name": "沈知遥",
        "role": "analyst",
        "unit": "设备可靠性组 · 可靠性分析",
        "daily_job_quota": 10,
    },
    {
        "email": "viewer@tsalign.demo",
        "display_name": "罗仲衡",
        "role": "viewer",
        "unit": "注塑车间 · 车间主管",
        "daily_job_quota": 0,
    },
]

# --------------------------------------------------------------------------
# persistence
# --------------------------------------------------------------------------
def _upsert_users(db) -> list[User]:
    users = []
    for spec in SEED_USERS:
        user = db.query(User).filter(User.email == spec["email"]).one_or_none()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(DEFAULT_PASSWORD),
                display_name=spec["display_name"],
                role=spec["role"],
                unit=spec["unit"],
                daily_job_quota=spec["daily_job_quota"],
            )
            db.add(user)
        else:
            user.display_name = spec["display_name"]
            user.role = spec["role"]
            user.unit = spec["unit"]
            user.daily_job_quota = spec["daily_job_quota"]
        users.append(user)
    db.commit()
    return users


def _upsert_sources(db) -> list[DataSource]:
    sources = []
    for spec in SEED_SOURCES:
        source = db.query(DataSource).filter(DataSource.code == spec["code"]).one_or_none()
        if source is None:
            source = DataSource(**spec)
            db.add(source)
        else:
            for key, value in spec.items():
                setattr(source, key, value)
        sources.append(source)
    db.commit()
    return sources


def _upsert_signals(db, sources: list[DataSource]) -> list[Signal]:
    source_by_code = {source.code: source for source in sources}
    signals = []
    for spec in SEED_SIGNALS:
        signal = db.query(Signal).filter(Signal.code == spec["code"]).one_or_none()
        source = source_by_code[spec["source"]]
        if signal is None:
            signal = Signal(
                code=spec["code"],
                source_id=source.id,
                device_code=spec["device_code"],
                device_name=spec["device_name"],
                measure_name=spec["measure_name"],
                tag_path=spec["tag_path"],
                unit=spec["unit"],
                sampling_interval_s=int(spec["cadence"]),
            )
            db.add(signal)
        else:
            signal.source_id = source.id
            signal.device_code = spec["device_code"]
            signal.device_name = spec["device_name"]
            signal.measure_name = spec["measure_name"]
            signal.tag_path = spec["tag_path"]
            signal.unit = spec["unit"]
            signal.sampling_interval_s = int(spec["cadence"])
        signals.append(signal)
    db.commit()
    return signals


def _persist_raw(db, signals: list[Signal], series: dict[str, list[tuple[float, float, int]]]) -> int:
    signal_by_code = {signal.code: signal for signal in signals}
    ids = [signal.id for signal in signals]
    existing = db.query(RawTelemetry).filter(RawTelemetry.signal_id.in_(ids)).count()
    expected = sum(len(rows) for rows in series.values())
    if existing != expected:
        db.query(RawTelemetry).filter(RawTelemetry.signal_id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        batch: list[RawTelemetry] = []
        for code, rows in series.items():
            signal = signal_by_code[code]
            for ts, value, seq in rows:
                batch.append(
                    RawTelemetry(
                        signal_id=signal.id,
                        source_id=signal.source_id,
                        ts=ts,
                        value=value,
                        seq=seq,
                    )
                )
            if len(batch) >= 1500:
                db.add_all(batch)
                db.commit()
                batch.clear()
        if batch:
            db.add_all(batch)
            db.commit()
    last_capture = {}
    for code, rows in series.items():
        source_code = next(spec["source"] for spec in SEED_SIGNALS if spec["code"] == code)
        latest = max(ts for ts, _value, _seq in rows)
        last_capture[source_code] = max(last_capture.get(source_code, 0.0), latest)
    for source in db.query(DataSource).all():
        latest = last_capture.get(source.code)
        if latest:
            source.last_capture_at = from_epoch(latest)
    db.commit()
    return db.query(RawTelemetry).filter(RawTelemetry.signal_id.in_(ids)).count()


def _persist_jobs_and_runs(db, signals: list[Signal], computed: list[dict]) -> tuple[list[AlignmentJob], list[AlignmentRun]]:
    signal_by_code = {signal.code: signal for signal in signals}
    user_by_email = {user.email: user for user in db.query(User).all()}
    jobs: list[AlignmentJob] = []
    runs: list[AlignmentRun] = []
    for item in computed:
        spec = item["job"]
        created_by = user_by_email[spec["engineer"]].id
        job = db.query(AlignmentJob).filter(AlignmentJob.name == spec["name"]).one_or_none()
        params = {
            "device_codes": spec["device_codes"],
            "signal_codes": item["codes"],
            "window_start": iso(spec["window_start"]),
            "window_end": iso(spec["window_end"]),
            "grid_s": spec["grid_s"],
            "agg_strategy": spec["agg_strategy"],
            "fill_strategy": spec["fill_strategy"],
        }
        if job is None:
            job = AlignmentJob(
                name=spec["name"],
                device_codes=spec["device_codes"],
                signal_codes=item["codes"],
                window_start=spec["window_start"],
                window_end=spec["window_end"],
                grid_s=spec["grid_s"],
                agg_strategy=spec["agg_strategy"],
                fill_strategy=spec["fill_strategy"],
                status=spec["status"],
                error_reason="",
                params_snapshot=params,
                note=spec["note"],
                created_by=created_by,
            )
            db.add(job)
            db.commit()
        else:
            job.device_codes = spec["device_codes"]
            job.signal_codes = item["codes"]
            job.window_start = spec["window_start"]
            job.window_end = spec["window_end"]
            job.grid_s = spec["grid_s"]
            job.agg_strategy = spec["agg_strategy"]
            job.fill_strategy = spec["fill_strategy"]
            job.params_snapshot = params
            job.note = spec["note"]
            db.commit()
        jobs.append(job)
        if spec["key"] == "pending":
            continue
        aligned = item["aligned"]
        gap_result = item["gaps"]
        run = db.query(AlignmentRun).filter(AlignmentRun.job_id == job.id).one_or_none()
        status = RunStatus.COMPLETED.value if gap_result and not gap_result.get("failure") else RunStatus.FAILED.value
        if aligned.get("failure"):
            status = RunStatus.FAILED.value
        components = (gap_result or {}).get("components") or {}
        result_json = {
            **aligned,
            "components": components,
            "series": (gap_result or {}).get("series") or [],
            "gaps": (gap_result or {}).get("gaps") or [],
            "window_start": iso(job.window_start),
            "window_end": iso(job.window_end),
            "agg_strategy": job.agg_strategy,
            "fill_strategy": job.fill_strategy,
        }
        if run is None:
            run = AlignmentRun(job_id=job.id)
            db.add(run)
        drifts = aligned.get("drift") or []
        max_drift = max(drifts, key=lambda value: abs(value["drift_ms"]), default={"drift_ms": 0.0})
        run.status = status
        run.finished_at = datetime(2026, 11, 10, 10, 31, 0)
        run.duration_ms = 1840 if status == RunStatus.COMPLETED.value else 220
        run.coverage_pct = round(float(aligned.get("coverage") or 0.0) * 100, 3)
        run.drift_ms = float(max_drift["drift_ms"])
        run.drift_confidence = float(aligned.get("drift_confidence") or 0.0)
        run.anomaly_rate = round(float(components.get("anomaly_rate") or 0.0) * 100, 3)
        run.quality_score = float(components.get("quality_score") or 0.0)
        run.gap_count = int(components.get("gap_count") or 0)
        run.gap_total_s = float(components.get("gap_total_s") or 0.0)
        run.point_count = int(aligned.get("point_count") or 0)
        run.bucket_count = int(aligned.get("bucket_count") or 0)
        run.failure_reason = aligned.get("failure") or ""
        run.result_json = result_json
        db.commit()
        db.refresh(run)
        runs.append(run)
        if gap_result and not gap_result.get("failure"):
            _upsert_gaps(db, run, gap_result["gaps"], signal_by_code)
    return jobs, runs


def _upsert_gaps(db, run: AlignmentRun, gaps: list[dict], signal_by_code: dict[str, Signal]) -> None:
    existing = {
        (gap.signal_id, float(gap.start_ts.timestamp())): gap
        for gap in db.query(GapEvent).filter(GapEvent.run_id == run.id).all()
    }
    seen: set[tuple[int, float]] = set()
    for payload in gaps:
        signal = signal_by_code[payload["signal_code"]]
        start_ts = from_epoch(float(payload["start_ts"]))
        end_ts = from_epoch(float(payload["end_ts"]))
        key = (signal.id, float(start_ts.timestamp()))
        seen.add(key)
        gap = existing.get(key)
        if gap is None:
            gap = GapEvent(run_id=run.id, signal_id=signal.id, start_ts=start_ts, end_ts=end_ts)
            db.add(gap)
        gap.start_ts = start_ts
        gap.end_ts = end_ts
        gap.duration_s = float(payload["duration_s"])
        gap.bucket_length = int(payload["bucket_length"])
        gap.fill_strategy = payload["fill_strategy"]
        gap.confidence = float(payload["confidence"])
        gap.severity = payload["severity"]
    for key, gap in existing.items():
        if key not in seen:
            db.delete(gap)
    db.commit()


def run_seed() -> dict:
    init_db()
    db = SessionLocal()
    try:
        users = _upsert_users(db)
        sources = _upsert_sources(db)
        signals = _upsert_signals(db, sources)
        series = build_seed_series()
        raw_points = _persist_raw(db, signals, series)
        computed = compute_seed_results(series)
        jobs, runs = _persist_jobs_and_runs(db, signals, computed)
        seeded_run_ids = [run.id for run in runs]
        gap_count = (
            db.query(GapEvent).filter(GapEvent.run_id.in_(seeded_run_ids)).count() if seeded_run_ids else 0
        )
        summary = {
            "sources": db.query(DataSource).filter(DataSource.code.in_([s["code"] for s in SEED_SOURCES])).count(),
            "signals": db.query(Signal).filter(Signal.code.in_([s["code"] for s in SEED_SIGNALS])).count(),
            "raw_points": raw_points,
            "jobs": db.query(AlignmentJob)
            .filter(AlignmentJob.name.in_([job["name"] for job in SEED_JOBS]))
            .count(),
            "gaps": gap_count,
            "users": db.query(User).filter(User.email.in_(SEED_EMAILS)).count(),
        }
        log_event("SEED_FINISHED", **summary)
        line = (
            f"SEED_SUMMARY sources={summary['sources']} signals={summary['signals']} "
            f"raw_points={summary['raw_points']} jobs={summary['jobs']} gaps={summary['gaps']} "
            f"users={summary['users']}"
        )
        print(line, flush=True)
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    result = run_seed()
    if not result:
        sys.exit(1)
