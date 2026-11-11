"""Data source & signal endpoints."""
from sqlalchemy.orm import Session

from src.middlewares.audit_logger import record
from src.services import signal_service, source_service


def list_sources(db: Session) -> dict:
    return {"items": [source_service.to_dict(source) for source in source_service.list_sources(db)]}


def source_detail(db: Session, source_id: int) -> dict:
    source = source_service.get_source(db, source_id)
    signals = source_service.signals_of(db, source_id)
    return {
        "source": source_service.to_dict(source),
        "signals": [source_service.signal_to_dict(signal) for signal in signals],
        "raw_point_count": source_service.raw_point_count(db, source_id),
        "signal_count": len(signals),
    }


def create_source(request, db: Session, payload) -> dict:
    source = source_service.create_source(db, payload)
    record(request, "source.create", "data_source", source.id, after={"code": source.code})
    return {"source": source_service.to_dict(source)}


def update_source(request, db: Session, source_id: int, payload) -> dict:
    before = source_service.to_dict(source_service.get_source(db, source_id))
    source = source_service.update_source(db, source_id, payload)
    record(request, "source.update", "data_source", source.id, before=before, after=source_service.to_dict(source))
    return {"source": source_service.to_dict(source)}


def list_signals(db: Session, device_code: str | None = None) -> dict:
    signals = signal_service.list_signals(db, device_code)
    return {"items": [source_service.signal_to_dict(signal) for signal in signals]}


def create_signal(request, db: Session, payload) -> dict:
    signal = signal_service.create_signal(db, payload)
    record(request, "signal.create", "signal", signal.id, after={"code": signal.code})
    return {"signal": source_service.signal_to_dict(signal)}
