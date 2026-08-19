from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends

from ..config import settings
from ..db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)) -> dict:
    database_ok = True
    try:
        db.execute(select(1))
    except Exception:
        database_ok = False

    nvidia_configured = bool(settings.nvidia_api_key)
    ok = database_ok
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ok" if ok else "unavailable",
        "database": database_ok,
        "nvidia_configured": nvidia_configured,
    }
