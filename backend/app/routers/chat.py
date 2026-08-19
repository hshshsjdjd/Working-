from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db, session_scope
from ..deps import AuthContext, get_client_ip, require_csrf
from ..models import (
    Conversation,
    MaintenanceState,
    Message,
    ModelConfig,
    UsageRecord,
    User,
    UserSettings,
)
from ..ratelimit import RateLimitExceeded, check_rate_limit
from ..schemas import ChatRequest, MessageOut
from ..services import nvidia
from ..services.context import build_messages

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _resolve_model(db: Session, requested: str | None, conv: Conversation, s: UserSettings) -> ModelConfig:
    candidate = requested or conv.model_id or (s.default_model_id if s else None)
    if candidate:
        model = db.get(ModelConfig, candidate)
        if model and model.enabled:
            return model
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected model is unavailable")
    model = db.execute(
        select(ModelConfig).where(ModelConfig.enabled.is_(True)).order_by(ModelConfig.sort_order)
    ).scalars().first()
    if not model:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="No models are enabled")
    return model


def _enforce_limits(db: Session, user: User, request: Request) -> None:
    ip = get_client_ip(request)
    try:
        check_rate_limit(f"chat:min:{user.id}", settings.max_requests_per_minute, 60)
        check_rate_limit(f"chat:ip:{ip}", settings.max_requests_per_minute, 60)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(exc.retry_after)},
        )
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily = db.execute(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user.id, UsageRecord.created_at >= start_of_day
        )
    ).scalar_one()
    if settings.max_daily_requests and daily >= settings.max_daily_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily request limit reached.",
        )


class _Prepared:
    def __init__(self, conv, model, api_messages, gen_params, user_content, regenerate):
        self.conv = conv
        self.model = model
        self.api_messages = api_messages
        self.gen_params = gen_params
        self.user_content = user_content
        self.regenerate = regenerate


def _prepare(db: Session, user: User, payload: ChatRequest, request: Request) -> _Prepared:
    if len(payload.content) > settings.max_message_length:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Message is too long")

    conv = db.get(Conversation, payload.conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    maintenance = db.get(MaintenanceState, 1)
    if maintenance and maintenance.maintenance_mode and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="The service is temporarily in maintenance mode.")

    s = db.get(UserSettings, user.id)
    _enforce_limits(db, user, request)
    model = _resolve_model(db, payload.model_id, conv, s)

    history_rows = db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    ).scalars().all()

    history = [{"role": m.role, "content": m.content} for m in history_rows if m.role in ("user", "assistant")]

    if payload.regenerate:
        # Drop a trailing assistant turn and regenerate from the last user turn.
        if history_rows and history_rows[-1].role == "assistant":
            db.delete(history_rows[-1])
            history = history[:-1]
        if not history or history[-1]["role"] != "user":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to regenerate")
    else:
        history.append({"role": "user", "content": payload.content})

    system_prompt = conv.system_prompt or (s.system_prompt if s else None)
    api_messages = build_messages(
        system_prompt=system_prompt,
        history=history,
        max_context_tokens=settings.max_context_tokens,
    )

    gen_params = {
        "temperature": payload.temperature if payload.temperature is not None else (s.temperature if s else 0.7),
        "top_p": payload.top_p if payload.top_p is not None else (s.top_p if s else 1.0),
        "max_tokens": payload.max_tokens if payload.max_tokens is not None else (s.max_tokens if s else 1024),
    }
    return _Prepared(conv, model, api_messages, gen_params, payload.content, payload.regenerate)


def _maybe_set_title(conv: Conversation, content: str) -> None:
    if conv.title in (None, "", "New chat"):
        conv.title = (content.strip().splitlines()[0] if content.strip() else "New chat")[:60] or "New chat"


def _record_usage(db, user_id, model_id, endpoint, success, latency_ms, usage: dict) -> None:
    db.add(
        UsageRecord(
            user_id=user_id,
            model_id=model_id,
            endpoint=endpoint,
            success=success,
            latency_ms=latency_ms,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
    )


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    ctx: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    user = ctx.user
    prepared = _prepare(db, user, payload, request)
    # Persist prep-stage deletions (regenerate) before streaming.
    db.commit()

    model_id = prepared.model.id
    conv_id = prepared.conv.id
    user_id = user.id
    api_messages = prepared.api_messages
    gen_params = prepared.gen_params
    user_content = prepared.user_content
    regenerate = prepared.regenerate

    async def event_stream():
        sess = session_scope()
        started = time.perf_counter()
        assistant_text = ""
        usage: dict = {}
        assistant_id = uuid.uuid4()
        try:
            conv = sess.get(Conversation, conv_id)
            if not regenerate:
                sess.add(Message(conversation_id=conv_id, user_id=user_id, role="user", content=user_content))
                _maybe_set_title(conv, user_content)
            assistant = Message(
                id=assistant_id, conversation_id=conv_id, user_id=user_id,
                role="assistant", content="", model_id=model_id,
            )
            sess.add(assistant)
            conv.model_id = model_id
            conv.updated_at = datetime.now(timezone.utc)
            sess.commit()

            yield _sse({"type": "meta", "message_id": str(assistant_id), "model_id": model_id})

            try:
                async for event in nvidia.stream_chat_completion(
                    model=model_id, messages=api_messages, **gen_params
                ):
                    if event["type"] == "delta":
                        assistant_text += event["content"]
                        yield _sse({"type": "delta", "content": event["content"]})
                    elif event["type"] == "done":
                        usage = event.get("usage") or {}
                        yield _sse({"type": "done", "finish_reason": event.get("finish_reason")})
            except nvidia.NvidiaConfigError:
                yield _sse({"type": "error", "category": "server_misconfigured",
                            "message": "The NVIDIA API is not configured on the server."})
                _finalize(sess, assistant_id, assistant_text, usage, conv_id, model_id, user_id,
                          started, success=False)
                return
            except nvidia.NvidiaAPIError as exc:
                yield _sse({"type": "error", "category": exc.category, "message": exc.message})
                _finalize(sess, assistant_id, assistant_text, usage, conv_id, model_id, user_id,
                          started, success=False)
                return

            _finalize(sess, assistant_id, assistant_text, usage, conv_id, model_id, user_id,
                      started, success=True)
        finally:
            # Persist any partial output on client disconnect / stop.
            try:
                if assistant_text:
                    row = sess.get(Message, assistant_id)
                    if row is not None and not row.content:
                        row.content = assistant_text
                        sess.commit()
            except Exception:
                sess.rollback()
            sess.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


def _finalize(sess, assistant_id, text, usage, conv_id, model_id, user_id, started, success):
    latency_ms = int((time.perf_counter() - started) * 1000)
    row = sess.get(Message, assistant_id)
    if row is not None:
        row.content = text
        row.prompt_tokens = usage.get("prompt_tokens")
        row.completion_tokens = usage.get("completion_tokens")
    _record_usage(sess, user_id, model_id, "chat_stream", success, latency_ms, usage)
    sess.commit()


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@router.post("", response_model=MessageOut)
async def chat(
    payload: ChatRequest,
    request: Request,
    ctx: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Message:
    user = ctx.user
    prepared = _prepare(db, user, payload, request)
    model_id = prepared.model.id
    started = time.perf_counter()

    if not prepared.regenerate:
        db.add(Message(conversation_id=prepared.conv.id, user_id=user.id, role="user", content=payload.content))
        _maybe_set_title(prepared.conv, payload.content)

    try:
        result = await nvidia.complete_chat(
            model=model_id, messages=prepared.api_messages, **prepared.gen_params
        )
    except nvidia.NvidiaConfigError:
        _record_usage(db, user.id, model_id, "chat", False, int((time.perf_counter() - started) * 1000), {})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="The NVIDIA API is not configured on the server.")
    except nvidia.NvidiaAPIError as exc:
        _record_usage(db, user.id, model_id, "chat", False, int((time.perf_counter() - started) * 1000), {})
        raise HTTPException(status_code=_status_for(exc.status_code), detail=exc.message)

    assistant = Message(
        conversation_id=prepared.conv.id, user_id=user.id, role="assistant",
        content=result.text, model_id=model_id,
        prompt_tokens=result.usage.get("prompt_tokens"),
        completion_tokens=result.usage.get("completion_tokens"),
    )
    db.add(assistant)
    prepared.conv.model_id = model_id
    prepared.conv.updated_at = datetime.now(timezone.utc)
    _record_usage(db, user.id, model_id, "chat", True, int((time.perf_counter() - started) * 1000), result.usage)
    db.flush()
    return assistant


def _status_for(upstream_status: int) -> int:
    if upstream_status in (401, 403):
        return status.HTTP_502_BAD_GATEWAY
    if upstream_status == 429:
        return status.HTTP_429_TOO_MANY_REQUESTS
    if upstream_status == 404:
        return status.HTTP_400_BAD_REQUEST
    return status.HTTP_502_BAD_GATEWAY
