from __future__ import annotations

import os
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user, require_csrf
from ..models import Conversation, FileObject, User
from ..schemas import FileOut

router = APIRouter(prefix="/api/files", tags=["files"])

_EXT_BY_MIME = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_name(name: str) -> str:
    base = os.path.basename(name or "file")
    base = base.replace("\x00", "")
    base = _FILENAME_RE.sub("_", base)
    return base[:200] or "file"


def _user_dir(user_id: uuid.UUID) -> str:
    path = os.path.join(settings.upload_dir, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


@router.post("", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: uuid.UUID | None = Form(default=None),
    user: User = Depends(get_current_user),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> FileObject:
    mime = (file.content_type or "").lower()
    if mime not in settings.allowed_mimetypes_set:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"File type '{mime}' is not allowed")

    original_name = _sanitize_name(file.filename or "file")
    ext = _EXT_BY_MIME.get(mime, "")
    provided_ext = os.path.splitext(original_name)[1].lower()
    # Reject dangerous extensions outright even if MIME says otherwise.
    if provided_ext in {".exe", ".sh", ".bat", ".cmd", ".js", ".php", ".py", ".dll", ".so"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="Executable uploads are not allowed")

    if conversation_id is not None:
        conv = db.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    # Stream to disk with a strict size cap.
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest_dir = _user_dir(user.id)
    dest_path = os.path.join(dest_dir, stored_name)
    # Ensure the resolved path stays inside the user's directory (defence in depth).
    if os.path.commonpath([os.path.realpath(dest_dir), os.path.realpath(dest_path)]) != os.path.realpath(dest_dir):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")

    size = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_file_size:
                    out.close()
                    os.remove(dest_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds the maximum allowed size",
                    )
                out.write(chunk)
    finally:
        await file.close()

    obj = FileObject(
        user_id=user.id,
        conversation_id=conversation_id,
        stored_name=stored_name,
        original_name=original_name,
        mime_type=mime,
        size_bytes=size,
    )
    db.add(obj)
    db.flush()
    return obj


@router.get("", response_model=list[FileOut])
def list_files(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FileObject]:
    stmt = select(FileObject).where(FileObject.user_id == user.id).order_by(FileObject.created_at.desc())
    return list(db.execute(stmt).scalars())


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: uuid.UUID,
    user: User = Depends(get_current_user),
    _: object = Depends(require_csrf),
    db: Session = Depends(get_db),
):
    obj = db.get(FileObject, file_id)
    if obj is None or obj.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    path = os.path.join(_user_dir(user.id), obj.stored_name)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
    db.delete(obj)
