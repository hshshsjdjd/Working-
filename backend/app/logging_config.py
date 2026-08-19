from __future__ import annotations

import logging

from pythonjsonlogger import json as jsonlogger

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "authorization",
    "api_key",
    "nvidia_api_key",
    "secret_key",
    "token",
    "session",
    "cookie",
}


class RedactingFilter(logging.Filter):
    """Best-effort redaction of sensitive keys from structured log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(vars(record).keys()):
            if key.lower() in _SENSITIVE_KEYS:
                setattr(record, key, "[redacted]")
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "time", "levelname": "level", "name": "logger"},
        )
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn access logs are noisy and can leak query strings; keep warnings+.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
