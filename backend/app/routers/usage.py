from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import UsageRecord, User, UserSettings
from ..schemas import UsageSummary

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("", response_model=UsageSummary)
def get_usage(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageSummary:
    total = db.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.user_id == user.id)
    ).scalar_one()
    successful = db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user.id, UsageRecord.success.is_(True)
        )
    ).scalar_one()
    # Only real token totals are summed; NULLs (unknown) are ignored, never invented.
    total_tokens = db.execute(
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0)).where(
            UsageRecord.user_id == user.id
        )
    ).scalar_one()

    recent_rows = db.execute(
        select(UsageRecord)
        .where(UsageRecord.user_id == user.id)
        .order_by(UsageRecord.created_at.desc())
        .limit(20)
    ).scalars()
    recent = [
        {
            "model_id": r.model_id,
            "endpoint": r.endpoint,
            "success": r.success,
            "latency_ms": r.latency_ms,
            "total_tokens": r.total_tokens,
            "created_at": r.created_at.isoformat(),
        }
        for r in recent_rows
    ]

    s = db.get(UserSettings, user.id)
    return UsageSummary(
        total_requests=total,
        successful_requests=successful,
        failed_requests=total - successful,
        total_tokens=int(total_tokens or 0),
        current_model=s.default_model_id if s else None,
        recent=recent,
    )
