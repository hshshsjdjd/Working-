from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_csrf
from ..models import User, UserSettings
from ..schemas import SettingsOut, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create(db: Session, user: User) -> UserSettings:
    s = db.get(UserSettings, user.id)
    if s is None:
        s = UserSettings(user_id=user.id)
        db.add(s)
        db.flush()
    return s


@router.get("", response_model=SettingsOut)
def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    return _get_or_create(db, user)


@router.patch("", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    user: User = Depends(get_current_user),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> UserSettings:
    s = _get_or_create(db, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, key, value)
    return s
