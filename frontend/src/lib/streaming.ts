import { csrfToken } from "./api";

export interface StreamHandlers {
  onMeta?: (data: { message_id: string; model_id: string }) => void;
  onDelta?: (text: string) => void;
  onDone?: (data: { finish_reason: string | null }) => void;
  onError?: (data: { category: string; message: string }) => void;
}

export interface ChatStreamBody {
  conversation_id: string;
  content: string;
  model_id?: string | null;
  regenerate?: boolean;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  file_ids?: string[];
}

/**
 * Streams a chat completion from the backend SSE endpoint, parsing events and
 * invoking the provided handlers. Pass an AbortSignal to support "Stop".
 */
export async function streamChat(
  body: ChatStreamBody,
  handlers: StreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const csrf = csrfToken();
  if (csrf) headers["X-CSRF-Token"] = csrf;

  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    handlers.onError?.({ category: "http_error", message: detail });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      let evt: Record<string, unknown>;
      try {
        evt = JSON.parse(payload);
      } catch {
        continue;
      }
      switch (evt.type) {
        case "meta":
          handlers.onMeta?.(evt as never);
          break;
        case "delta":
          handlers.onDelta?.(String(evt.content ?? ""));
          break;
        case "done":
          handlers.onDone?.(evt as never);
          break;
        case "error":
          handlers.onError?.(evt as never);
          break;
      }
    }
  }
}
