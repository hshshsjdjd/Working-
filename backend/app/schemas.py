from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)

    @field_validator("password")
    @classmethod
    def _password_strength(cls, v: str) -> str:
        if v.strip() == "" or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


# ---- Models ----
class ModelOut(ORMModel):
    id: str
    display_name: str
    description: str
    capabilities: list[str]
    context_window: int
    supports_vision: bool
    enabled: bool
    sort_order: int


class ModelAdminUpdate(BaseModel):
    enabled: bool | None = None
    sort_order: int | None = None
    display_name: str | None = None
    description: str | None = None


# ---- Conversations ----
class ConversationCreate(BaseModel):
    title: str = Field(default="New chat", max_length=255)
    model_id: str | None = Field(default=None, max_length=128)
    system_prompt: str | None = Field(default=None, max_length=8000)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=128)
    system_prompt: str | None = Field(default=None, max_length=8000)
    pinned: bool | None = None
    archived: bool | None = None


class ConversationOut(ORMModel):
    id: uuid.UUID
    title: str
    model_id: str | None
    system_prompt: str | None
    pinned: bool
    archived: bool
    created_at: datetime
    updated_at: datetime


class MessageOut(ORMModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    model_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


# ---- Chat ----
class ChatRequest(BaseModel):
    conversation_id: uuid.UUID
    content: str = Field(min_length=1)
    model_id: str | None = Field(default=None, max_length=128)
    regenerate: bool = False
    # Optional overrides; fall back to user settings when omitted.
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    file_ids: list[uuid.UUID] = Field(default_factory=list)


# ---- Settings ----
class SettingsOut(ORMModel):
    theme: str
    default_model_id: str | None
    temperature: float
    top_p: float
    max_tokens: int
    system_prompt: str | None
    streaming: bool
    markdown: bool
    code_highlight: bool
    auto_scroll: bool


class SettingsUpdate(BaseModel):
    theme: Literal["dark", "light", "system", "amoled"] | None = None
    default_model_id: str | None = Field(default=None, max_length=128)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    system_prompt: str | None = Field(default=None, max_length=8000)
    streaming: bool | None = None
    markdown: bool | None = None
    code_highlight: bool | None = None
    auto_scroll: bool | None = None


# ---- Files ----
class FileOut(ORMModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    conversation_id: uuid.UUID | None
    created_at: datetime


# ---- Usage ----
class UsageSummary(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    current_model: str | None
    recent: list[dict[str, Any]]


# ---- Admin ----
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    total_requests: int
    total_errors: int
    model_usage: list[dict[str, Any]]
    database_ok: bool
    maintenance_mode: bool
