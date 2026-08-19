from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import ModelConfig, User
from ..schemas import ModelOut

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelOut])
def list_models(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ModelConfig]:
    stmt = (
        select(ModelConfig)
        .where(ModelConfig.enabled.is_(True))
        .order_by(ModelConfig.sort_order, ModelConfig.display_name)
    )
    return list(db.execute(stmt).scalars())
