"""Signal catalog queries and lookups used by job creation / alignment."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.error_codes import AppError, ErrorCode
from src.models import RawTelemetry, Signal


def list_signals(db: Session, device_code: str | None = None) -> list[Signal]:
    statement = select(Signal).order_by(Signal.device_code, Signal.id)
    if device_code:
        statement = statement.where(Signal.device_code == device_code)
    return list(db.scalars(statement))


def get_signal(db: Session, signal_id: int) -> Signal:
    signal = db.get(Signal, signal_id)
    if signal is None:
        raise AppError(ErrorCode.NOT_FOUND, "测点不存在", status_code=404)
    return signal


def signals_for_devices(db: Session, device_codes: list[str]) -> list[Signal]:
    codes = [code.strip() for code in device_codes if code.strip()]
    if not codes:
        raise AppError(ErrorCode.VALIDATION_FAILED, "至少选择一个设备", status_code=422)
    rows = list(
        db.scalars(
            select(Signal)
            .where(Signal.device_code.in_(codes), Signal.is_active.is_(True))
            .order_by(Signal.device_code, Signal.id)
        )
    )
    if not rows:
        raise AppError(ErrorCode.NOT_FOUND, "所选设备下没有可用测点", status_code=404)
    return rows


def point_count(db: Session, signal_ids: list[int], start: float, end: float) -> int:
    if not signal_ids:
        return 0
    return int(
        db.scalar(
            select(func.count(RawTelemetry.id)).where(
                RawTelemetry.signal_id.in_(signal_ids),
                RawTelemetry.ts >= start,
                RawTelemetry.ts <= end,
            )
        )
        or 0
    )


def create_signal(db: Session, payload) -> Signal:
    existing = db.scalar(select(Signal).where(Signal.code == payload.code))
    if existing is not None:
        raise AppError(ErrorCode.CONFLICT, "测点编码已存在", status_code=409)
    signal = Signal(
        code=payload.code,
        source_id=payload.source_id,
        device_code=payload.device_code,
        device_name=payload.device_name,
        measure_name=payload.measure_name,
        tag_path=payload.tag_path,
        unit=payload.unit,
        sampling_interval_s=payload.sampling_interval_s,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal
