from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy.orm import Session

from .config import settings
from .models import Session as SessionModel
from .security import (
    generate_csrf_token,
    generate_session_token,
    hash_session_token,
)


def create_session(
    db: Session,
    *,
    user_id,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[SessionModel, str]:
    """Create a DB-backed session; returns (session, raw_token)."""
    raw_token = generate_session_token()
    csrf_token = generate_csrf_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.session_ttl_hours)
    session = SessionModel(
        user_id=user_id,
        token_hash=hash_session_token(raw_token),
        csrf_token=csrf_token,
        user_agent=(user_agent or "")[:512],
        ip_address=(ip_address or "")[:64],
        expires_at=expires_at,
    )
    db.add(session)
    db.flush()
    return session, raw_token


def set_session_cookies(response: Response, *, raw_token: str, csrf_token: str) -> None:
    max_age = settings.session_ttl_hours * 3600
    # Session cookie: HTTP-only, not readable by JS.
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        path="/",
    )
    # CSRF cookie: readable by JS so the SPA can echo it in a header (double submit).
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
