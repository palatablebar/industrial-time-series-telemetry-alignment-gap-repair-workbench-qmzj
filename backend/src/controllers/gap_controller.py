"""Gap event endpoints: list + analyst annotation."""
from sqlalchemy.orm import Session

from src.middlewares.audit_logger import record
from src.services import gap_service


def list_gaps(
    db: Session,
    run_id: int | None = None,
    severity: str | None = None,
    device_code: str | None = None,
) -> dict:
    items = gap_service.list_gaps(db, run_id=run_id, severity=severity, device_code=device_code)
    return {"items": items, "total": len(items)}


def annotate_gap(request, db: Session, gap_id: int, payload) -> dict:
    gap = gap_service.annotate(db, gap_id, payload.annotation)
    record(request, "gap_event.annotate", "gap_event", gap.id, after={"annotation": gap.annotation})
    return {
        "gap": {
            "id": gap.id,
            "annotated": gap.annotated,
            "annotation": gap.annotation,
        }
    }
