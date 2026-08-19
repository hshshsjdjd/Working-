from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Secrets (NVIDIA_API_KEY, SECRET_KEY, DATABASE_URL) are only ever read from
    the server environment. They are never sent to the browser or logged.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development")
    app_name: str = Field(default="NVIDIA AI")
    secret_key: str = Field(default="dev-insecure-change-me")

    database_url: str = Field(
        default="postgresql+psycopg://nvidia:nvidia@localhost:5432/nvidia_ai"
    )

    # NVIDIA API
    nvidia_api_key: str = Field(default="")
    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1")
    nvidia_timeout_seconds: float = Field(default=60.0)
    nvidia_max_retries: int = Field(default=2)

    # Cookies / sessions
    session_cookie_name: str = Field(default="nvai_session")
    csrf_cookie_name: str = Field(default="nvai_csrf")
    session_ttl_hours: int = Field(default=24 * 14)
    cookie_secure: bool | None = Field(default=None)
    cookie_samesite: str = Field(default="lax")

    # CORS – comma separated list of allowed origins for the browser app.
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:8080")

    # Rate limiting / limits
    max_requests_per_minute: int = Field(default=60)
    max_daily_requests: int = Field(default=1000)
    auth_max_attempts_per_minute: int = Field(default=10)
    max_file_size: int = Field(default=10 * 1024 * 1024)  # 10 MiB
    max_message_length: int = Field(default=32000)
    max_context_tokens: int = Field(default=8000)

    # Uploads
    upload_dir: str = Field(default="/data/uploads")
    allowed_upload_mimetypes: str = Field(
        default=(
            "text/plain,text/markdown,text/csv,application/json,application/pdf,"
            "image/png,image/jpeg,image/webp,image/gif"
        )
    )

    @field_validator("cookie_samesite")
    @classmethod
    def _validate_samesite(cls, value: str) -> str:
        value = value.lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("cookie_samesite must be one of lax, strict, none")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_mimetypes_set(self) -> set[str]:
        return {m.strip() for m in self.allowed_upload_mimetypes.split(",") if m.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
