from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Session as SessionModel
from .models import User
from .security import constant_time_equals, hash_session_token

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_client_ip(request: Request) -> str:
    # Caddy/Nginx set X-Forwarded-For; take the left-most (original client).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _load_session(db: Session, token: str) -> SessionModel | None:
    token_hash = hash_session_token(token)
    stmt = select(SessionModel).where(SessionModel.token_hash == token_hash)
    session = db.execute(stmt).scalar_one_or_none()
    if session is None:
        return None
    if session.revoked_at is not None:
        return None
    if session.expires_at <= datetime.now(timezone.utc):
        return None
    return session


class AuthContext:
    def __init__(self, user: User, session: SessionModel) -> None:
        self.user = user
        self.session = session


def get_auth_context(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    session = _load_session(db, token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    return AuthContext(user=user, session=session)


def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


def require_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    ctx: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    """Double-submit CSRF protection bound to the authenticated session."""
    if request.method in SAFE_METHODS:
        return ctx
    if not x_csrf_token or not constant_time_equals(x_csrf_token, ctx.session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid"
        )
    return ctx


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
