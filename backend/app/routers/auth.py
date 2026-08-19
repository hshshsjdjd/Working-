from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import settings
from ..cookies import clear_session_cookies, create_session, set_session_cookies
from ..db import get_db
from ..deps import AuthContext, get_auth_context, get_client_ip, require_csrf
from ..models import Session as SessionModel
from ..models import User, UserSettings
from ..ratelimit import RateLimitExceeded, check_rate_limit
from ..schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from ..security import hash_password, needs_rehash, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_rate_limit(request: Request, bucket: str) -> None:
    ip = get_client_ip(request)
    try:
        check_rate_limit(f"auth:{bucket}:{ip}", settings.auth_max_attempts_per_minute, 60)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait and try again.",
            headers={"Retry-After": str(exc.retry_after)},
        )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    _auth_rate_limit(request, "register")
    email = payload.email.lower().strip()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        # Do not reveal whether the email exists.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to register")

    is_first_user = db.execute(select(func.count(User.id))).scalar_one() == 0
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role="admin" if is_first_user else "user",
    )
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id, theme="amoled"))

    session, raw_token = create_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=get_client_ip(request),
    )
    set_session_cookies(response, raw_token=raw_token, csrf_token=session.csrf_token)
    record_audit(db, action="register", user_id=user.id, ip_address=get_client_ip(request))
    return user


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    _auth_rate_limit(request, "login")
    email = payload.email.lower().strip()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    # Constant-ish behaviour: always run a verify to reduce user enumeration.
    valid = bool(user) and verify_password(payload.password, user.password_hash)
    if not user or not valid:
        record_audit(db, action="login_failed", ip_address=get_client_ip(request),
                     detail={"email": email})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    session, raw_token = create_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=get_client_ip(request),
    )
    set_session_cookies(response, raw_token=raw_token, csrf_token=session.csrf_token)
    record_audit(db, action="login", user_id=user.id, ip_address=get_client_ip(request))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    ctx: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    ctx.session.revoked_at = datetime.now(timezone.utc)
    clear_session_cookies(response)
    record_audit(db, action="logout", user_id=ctx.user.id)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    ctx: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(payload.current_password, ctx.user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    ctx.user.password_hash = hash_password(payload.new_password)

    # Revoke all other sessions for safety; keep the current one alive.
    others = db.execute(
        select(SessionModel).where(
            SessionModel.user_id == ctx.user.id, SessionModel.id != ctx.session.id
        )
    ).scalars()
    now = datetime.now(timezone.utc)
    for s in others:
        s.revoked_at = now
    record_audit(db, action="change_password", user_id=ctx.user.id)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    ctx: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(payload.password, ctx.user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect")
    # Cascades remove conversations, messages, files, settings, sessions.
    db.delete(ctx.user)
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
