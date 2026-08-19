from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..db import get_db
from ..deps import require_admin, require_csrf
from ..models import (
    AuditLog,
    MaintenanceState,
    ModelConfig,
    UsageRecord,
    User,
)
from ..schemas import AdminStats, ModelAdminUpdate, ModelOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _maintenance(db: Session) -> MaintenanceState:
    state = db.get(MaintenanceState, 1)
    if state is None:
        state = MaintenanceState(id=1, maintenance_mode=False)
        db.add(state)
        db.flush()
    return state


@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminStats:
    total_users = db.execute(select(func.count(User.id))).scalar_one()
    active_users = db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    ).scalar_one()
    total_requests = db.execute(select(func.count(UsageRecord.id))).scalar_one()
    total_errors = db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.success.is_(False))
    ).scalar_one()
    model_usage_rows = db.execute(
        select(UsageRecord.model_id, func.count(UsageRecord.id))
        .group_by(UsageRecord.model_id)
        .order_by(func.count(UsageRecord.id).desc())
    ).all()
    model_usage = [{"model_id": mid, "requests": count} for mid, count in model_usage_rows]

    database_ok = True
    try:
        db.execute(select(1))
    except Exception:
        database_ok = False

    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_requests=total_requests,
        total_errors=total_errors,
        model_usage=model_usage,
        database_ok=database_ok,
        maintenance_mode=_maintenance(db).maintenance_mode,
    )


@router.get("/models", response_model=list[ModelOut])
def admin_list_models(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[ModelConfig]:
    return list(db.execute(select(ModelConfig).order_by(ModelConfig.sort_order)).scalars())


@router.patch("/models/{model_id:path}", response_model=ModelOut)
def update_model(
    model_id: str,
    payload: ModelAdminUpdate,
    admin: User = Depends(require_admin),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> ModelConfig:
    model = db.get(ModelConfig, model_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    record_audit(db, action="model_update", user_id=admin.id, detail={"model_id": model_id})
    return model


@router.post("/users/{user_id}/active", status_code=status.HTTP_204_NO_CONTENT)
def set_user_active(
    user_id: uuid.UUID,
    active: bool,
    admin: User = Depends(require_admin),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == admin.id and not active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own account")
    target.is_active = active
    record_audit(db, action="user_active_toggle", user_id=admin.id,
                 detail={"target": str(user_id), "active": active})


@router.post("/maintenance", status_code=status.HTTP_204_NO_CONTENT)
def set_maintenance(
    enabled: bool,
    admin: User = Depends(require_admin),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    state = _maintenance(db)
    state.maintenance_mode = enabled
    record_audit(db, action="maintenance_toggle", user_id=admin.id, detail={"enabled": enabled})


@router.get("/audit", response_model=list[dict])
def list_audit(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).scalars()
    return [
        {
            "action": r.action,
            "user_id": str(r.user_id) if r.user_id else None,
            "ip_address": r.ip_address,
            "detail": r.detail,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
