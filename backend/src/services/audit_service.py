"""Read side of the audit log."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import AuditLog, User
from src.utils.timeutil import iso


def recent(db: Session, limit: int = 30) -> list[dict]:
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)))
    actors = {user.id: user.display_name for user in db.scalars(select(User))}
    return [
        {
            "id": row.id,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "actor": actors.get(row.actor_id, "系统"),
            "ip": row.ip,
            "created_at": iso(row.created_at),
        }
        for row in rows
    ]
