from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from .models import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(action=action, user_id=user_id, ip_address=ip_address, detail=detail or {})
    )
