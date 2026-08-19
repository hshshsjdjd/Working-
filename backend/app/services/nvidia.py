from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger("app.nvidia")


class NvidiaConfigError(RuntimeError):
    """Raised when the server is missing NVIDIA credentials."""


@dataclass
class NvidiaAPIError(Exception):
    status_code: int
    category: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.category}: {self.message}"


@dataclass
class StreamResult:
    """Accumulated result of a streamed completion."""

    text: str = ""
    finish_reason: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


def _headers() -> dict[str, str]:
    if not settings.nvidia_api_key:
        raise NvidiaConfigError("NVIDIA_API_KEY is not configured on the server")
    return {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }


def _categorize(status_code: int) -> str:
    if status_code in (401, 403):
        return "invalid_api_key"
    if status_code == 404:
        return "model_unavailable"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "upstream_unavailable"
    return "upstream_error"


def _build_payload(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream: bool,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    if stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


async def stream_chat_completion(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> AsyncIterator[dict[str, Any]]:
    """Yield events from the NVIDIA OpenAI-compatible streaming endpoint.

    Event shapes:
      {"type": "delta", "content": "..."}
      {"type": "done", "finish_reason": str|None, "usage": {...}}

    Retries are only attempted before the first byte is received so partial
    output is never duplicated. If the consumer stops iterating (client
    disconnect / stop button), the httpx stream is aborted via the context
    manager, cancelling the upstream request.
    """
    payload = _build_payload(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=True,
    )
    headers = _headers()
    url = f"{settings.nvidia_base_url.rstrip('/')}/chat/completions"

    attempt = 0
    while True:
        attempt += 1
        try:
            async with httpx.AsyncClient(timeout=settings.nvidia_timeout_seconds) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "ignore")
                        category = _categorize(resp.status_code)
                        retryable = resp.status_code in (429, 500, 502, 503, 504)
                        if retryable and attempt <= settings.nvidia_max_retries:
                            await asyncio.sleep(min(2 ** attempt, 8))
                            continue
                        raise NvidiaAPIError(resp.status_code, category, _safe_error(body))
                    usage: dict[str, Any] = {}
                    finish_reason: str | None = None
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        if chunk.get("usage"):
                            usage = chunk["usage"]
                        for choice in chunk.get("choices", []) or []:
                            delta = choice.get("delta") or {}
                            content = delta.get("content")
                            if content:
                                yield {"type": "delta", "content": content}
                            if choice.get("finish_reason"):
                                finish_reason = choice["finish_reason"]
                    yield {"type": "done", "finish_reason": finish_reason, "usage": usage}
                    return
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if attempt <= settings.nvidia_max_retries:
                await asyncio.sleep(min(2 ** attempt, 8))
                continue
            raise NvidiaAPIError(504, "timeout", "The NVIDIA API timed out") from exc


async def complete_chat(
    *,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> StreamResult:
    """Non-streaming completion (used by tests and the non-stream endpoint)."""
    payload = _build_payload(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=False,
    )
    headers = {k: v for k, v in _headers().items() if k != "Accept"}
    url = f"{settings.nvidia_base_url.rstrip('/')}/chat/completions"

    attempt = 0
    while True:
        attempt += 1
        try:
            async with httpx.AsyncClient(timeout=settings.nvidia_timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    if resp.status_code in (429, 500, 502, 503, 504) and attempt <= settings.nvidia_max_retries:
                        await asyncio.sleep(min(2 ** attempt, 8))
                        continue
                    raise NvidiaAPIError(
                        resp.status_code, _categorize(resp.status_code), _safe_error(resp.text)
                    )
                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                return StreamResult(
                    text=message.get("content") or "",
                    finish_reason=choice.get("finish_reason"),
                    usage=data.get("usage") or {},
                )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            if attempt <= settings.nvidia_max_retries:
                await asyncio.sleep(min(2 ** attempt, 8))
                continue
            raise NvidiaAPIError(504, "timeout", "The NVIDIA API timed out") from exc


def _safe_error(body: str) -> str:
    """Extract a short, non-sensitive error message from an upstream body."""
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            detail = parsed.get("detail") or parsed.get("error") or parsed.get("message")
            if isinstance(detail, dict):
                detail = detail.get("message")
            if detail:
                return str(detail)[:300]
    except (json.JSONDecodeError, TypeError):
        pass
    return (body or "Upstream error")[:300]
