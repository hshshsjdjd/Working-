from __future__ import annotations

from typing import Any

# Rough heuristic: ~4 characters per token. Good enough for budgeting; the
# server never fabricates exact token counts (those come from NVIDIA usage).
_CHARS_PER_TOKEN = 4
_PER_MESSAGE_OVERHEAD_TOKENS = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN) + _PER_MESSAGE_OVERHEAD_TOKENS


def build_messages(
    *,
    system_prompt: str | None,
    history: list[dict[str, str]],
    max_context_tokens: int,
) -> list[dict[str, Any]]:
    """Construct the final message list within the context budget.

    Order preserved: system prompt first, then the most recent history that
    fits. The final (current) user message is always kept — the current request
    is never silently dropped.
    """
    budget = max(1, max_context_tokens)
    out: list[dict[str, Any]] = []

    system_tokens = 0
    if system_prompt and system_prompt.strip():
        system_tokens = estimate_tokens(system_prompt)
        budget -= system_tokens

    if not history:
        result: list[dict[str, Any]] = []
        if system_prompt and system_prompt.strip():
            result.append({"role": "system", "content": system_prompt})
        return result

    # Always keep the last message (current user turn).
    kept: list[dict[str, str]] = []
    last = history[-1]
    kept.append(last)
    budget -= estimate_tokens(last["content"])

    # Walk backwards through the earlier history, newest first.
    for msg in reversed(history[:-1]):
        cost = estimate_tokens(msg["content"])
        if budget - cost < 0:
            break
        budget -= cost
        kept.append(msg)

    kept.reverse()

    if system_prompt and system_prompt.strip():
        out.append({"role": "system", "content": system_prompt})
    out.extend({"role": m["role"], "content": m["content"]} for m in kept)
    return out
