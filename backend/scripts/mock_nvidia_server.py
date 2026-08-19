"""DEV/TEST ONLY OpenAI-compatible mock of the NVIDIA endpoint.

This is NOT part of the production application and is never deployed. It exists
so the streaming pipeline can be exercised end-to-end locally without a real
NVIDIA_API_KEY. Point NVIDIA_BASE_URL at it, e.g.:

    NVIDIA_BASE_URL=http://localhost:9999/v1
    NVIDIA_API_KEY=dev-key

Run: python -m scripts.mock_nvidia_server
"""
from __future__ import annotations

import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "mock-model")
    stream = body.get("stream", False)
    last_user = ""
    for m in body.get("messages", []):
        if m.get("role") == "user":
            last_user = m.get("content", "")
    reply = (
        f"Here is a mock streamed answer about: '{last_user[:60]}'.\n\n"
        "```python\nprint('hello from the mock NVIDIA server')\n```\n\n"
        "This confirms the backend streaming proxy works end to end."
    )

    if not stream:
        return {
            "id": "mock",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": reply},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 40, "total_tokens": 52},
        }

    def gen():
        for token in reply.split(" "):
            chunk = {
                "id": "mock",
                "model": model,
                "choices": [{"index": 0, "delta": {"content": token + " "}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            time.sleep(0.02)
        final = {
            "id": "mock",
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 40, "total_tokens": 52},
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9999, log_level="warning")
