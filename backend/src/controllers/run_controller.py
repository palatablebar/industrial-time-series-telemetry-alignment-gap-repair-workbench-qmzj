"""Alignment run endpoints + CSV export."""
from urllib.parse import quote

from fastapi import Response
from sqlalchemy.orm import Session

from src.middlewares.audit_logger import record
from src.services import run_service


def list_runs(db: Session) -> dict:
    return {"items": [run_service.to_dict(db, run) for run in run_service.list_runs(db)]}


def run_detail(db: Session, run_id: int) -> dict:
    return {"run": run_service.to_detail(db, run_service.get_run(db, run_id))}


def export_run_csv(request, db: Session, run_id: int) -> Response:
    content, filename, row_count = run_service.export_csv(db, run_id)
    record(request, "alignment_run.export", "alignment_run", run_id, after={"rows": row_count})
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "X-CSV-Rows": str(row_count),
    }
    return Response(content=content.encode("utf-8-sig"), media_type="text/csv; charset=utf-8", headers=headers)
