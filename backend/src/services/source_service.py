"""Data-source CRUD with audit-friendly projections."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.error_codes import AppError, ErrorCode
from src.models import DataSource, RawTelemetry, Signal


def list_sources(db: Session) -> list[DataSource]:
    return list(db.scalars(select(DataSource).order_by(DataSource.id)))


def get_source(db: Session, source_id: int) -> DataSource:
    source = db.get(DataSource, source_id)
    if source is None:
        raise AppError(ErrorCode.NOT_FOUND, "数据源不存在", status_code=404)
    return source


def signals_of(db: Session, source_id: int) -> list[Signal]:
    return list(
        db.scalars(select(Signal).where(Signal.source_id == source_id).order_by(Signal.device_code, Signal.id))
    )


def raw_point_count(db: Session, source_id: int) -> int:
    return int(db.scalar(select(func.count(RawTelemetry.id)).where(RawTelemetry.source_id == source_id)) or 0)


def to_dict(source: DataSource) -> dict:
    return {
        "id": source.id,
        "code": source.code,
        "name": source.name,
        "protocol": source.protocol,
        "sample_interval_s": source.sample_interval_s,
        "timezone": source.timezone,
        "drift_hint_ms": source.drift_hint_ms,
        "status": source.status,
        "workshop": source.workshop,
        "description": source.description,
        "last_capture_at": source.last_capture_at.strftime("%Y-%m-%dT%H:%M:%S")
        if source.last_capture_at
        else None,
    }


def signal_to_dict(signal: Signal) -> dict:
    return {
        "id": signal.id,
        "code": signal.code,
        "source_id": signal.source_id,
        "device_code": signal.device_code,
        "device_name": signal.device_name,
        "measure_name": signal.measure_name,
        "tag_path": signal.tag_path,
        "unit": signal.unit,
        "sampling_interval_s": signal.sampling_interval_s,
        "is_active": signal.is_active,
        "scale_min": signal.scale_min,
        "scale_max": signal.scale_max,
    }


def update_source(db: Session, source_id: int, payload) -> DataSource:
    source = get_source(db, source_id)
    if payload.name is not None:
        source.name = payload.name
    if payload.status is not None:
        source.status = payload.status
    if payload.drift_hint_ms is not None:
        source.drift_hint_ms = payload.drift_hint_ms
    if payload.description is not None:
        source.description = payload.description
    db.commit()
    db.refresh(source)
    return source


def create_source(db: Session, payload) -> DataSource:
    existing = db.scalar(select(DataSource).where(DataSource.code == payload.code))
    if existing is not None:
        raise AppError(ErrorCode.CONFLICT, "数据源编码已存在", status_code=409)
    source = DataSource(
        code=payload.code,
        name=payload.name,
        protocol=payload.protocol,
        sample_interval_s=payload.sample_interval_s,
        workshop=payload.workshop,
        description=payload.description,
        status="online",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
