export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

const CSRF_COOKIE = "nvai_csrf";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

interface Options {
  method?: string;
  body?: unknown;
  raw?: boolean;
}

export async function api<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const method = opts.method || "GET";
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (opts.body !== undefined && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  } else if (opts.body instanceof FormData) {
    body = opts.body;
  }

  if (UNSAFE.has(method)) {
    const csrf = getCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(path, {
    method,
    headers,
    body,
    credentials: "include",
  });

  if (res.status === 204) return undefined as T;

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = typeof data.detail === "string" ? data.detail : detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }

  if (opts.raw) return res as unknown as T;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

export function csrfToken(): string | null {
  return getCookie(CSRF_COOKIE);
}
