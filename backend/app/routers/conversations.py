from __future__ import annotations

import io
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_csrf
from ..models import Conversation, Message, User
from ..schemas import (
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _get_owned_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    # IDOR protection: identity comes from the session, never the client.
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    archived: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=255),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    stmt = select(Conversation).where(
        Conversation.user_id == user.id,
        Conversation.archived.is_(archived),
    )
    if search:
        stmt = stmt.where(Conversation.title.ilike(f"%{search}%"))
    stmt = stmt.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc())
    return list(db.execute(stmt).scalars())


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Conversation:
    conv = Conversation(
        user_id=user.id,
        title=payload.title or "New chat",
        model_id=payload.model_id,
        system_prompt=payload.system_prompt,
    )
    db.add(conv)
    db.flush()
    return conv


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    return _get_owned_conversation(db, user, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationOut)
def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    user: User = Depends(get_current_user),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> Conversation:
    conv = _get_owned_conversation(db, user, conversation_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(conv, key, value)
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    conv = _get_owned_conversation(db, user, conversation_id)
    db.delete(conv)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Message]:
    _get_owned_conversation(db, user, conversation_id)
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(db.execute(stmt).scalars())


@router.get("/{conversation_id}/export")
def export_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    conv = _get_owned_conversation(db, user, conversation_id)
    messages = db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
    ).scalars()
    export = {
        "title": conv.title,
        "model_id": conv.model_id,
        "system_prompt": conv.system_prompt,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
    }
    buf = io.BytesIO(json.dumps(export, indent=2).encode("utf-8"))
    filename = f"conversation-{conv.id}.json"
    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
