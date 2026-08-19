# Security model & review

This document summarizes the controls in place and the review performed before
declaring the build complete.

## Authentication & sessions

- Passwords hashed with **Argon2id** (`argon2-cffi`), never stored or logged in plaintext.
- Sessions are opaque high-entropy tokens; only a **SHA-256 hash** of the token is stored server-side. The raw token lives only in an **HTTP-only** cookie.
- Cookies are `Secure` in production, `SameSite=Lax`, scoped to `/`.
- Login/registration are rate-limited per IP; failed logins are audited; responses avoid user enumeration.
- Changing the password revokes all other sessions.

## Authorization / IDOR

- Identity is always derived from the server-side session — **never** from a client-supplied user ID.
- Every conversation/message/file query is scoped to the authenticated user; cross-user access returns `404`.
- Admin endpoints require the `admin` role (role-based access control).

## CSRF

- Double-submit CSRF: a readable `nvai_csrf` cookie is bound to the session's stored token; all unsafe methods (`POST/PUT/PATCH/DELETE`) require a matching `X-CSRF-Token` header, compared in constant time.

## Injection

- **SQL injection**: all DB access uses SQLAlchemy ORM / parameterized queries. No string-built SQL.
- **XSS**: API responses are JSON; the SPA renders Markdown via `react-markdown` (no `dangerouslySetInnerHTML`, no raw HTML injection).
- **SSRF**: the backend only ever calls the configured `NVIDIA_BASE_URL`; user input never selects the upstream host.

## Uploads

- Validated by MIME allow-list, extension checks, and an explicit executable-extension deny-list.
- Size-capped while streaming to disk (`MAX_FILE_SIZE`).
- Stored under per-user directories with random UUID filenames; original names are sanitized; resolved paths are verified to stay within the user's directory (path-traversal defense).

## Transport & headers

- HTTPS enforced at the edge (Caddy); HTTP→HTTPS handled by Caddy when a domain is set.
- Security headers: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, HSTS (production).
- Strict CORS allow-list with credentials; only required methods/headers permitted.

## Secrets

- `NVIDIA_API_KEY`, `SECRET_KEY`, `DATABASE_URL` are read from the server environment only.
- Never sent to the browser, embedded in the bundle, put in URLs/storage, returned in responses, or logged. A logging filter redacts sensitive keys, and structured request logs exclude bodies/headers.

## Rate limiting & abuse

- Configurable per-minute and per-day limits on chat; per-IP limits on auth and chat. Returns `429` with `Retry-After`.
- Message length and context size are bounded; oversized requests return `413`.

## Error handling

- A global handler returns generic JSON errors with a request ID; **production stack traces are never returned** to clients (full detail is logged server-side).

## Review checklist (performed)

| Area | Status |
| --- | --- |
| Authentication (Argon2id, sessions) | ✅ |
| Authorization / IDOR (ownership scoping) | ✅ (tested) |
| Session security (HTTP-only, hashed, revocation) | ✅ |
| CSRF (double submit, required on mutations) | ✅ (tested) |
| XSS (no raw HTML) | ✅ |
| SQL injection (ORM/parameterized) | ✅ |
| SSRF (fixed upstream) | ✅ |
| File upload security | ✅ (tested) |
| Rate limiting | ✅ (tested) |
| Secret management / no key exposure | ✅ (tested) |
| HTTPS / CORS / security headers | ✅ (tested headers) |

## Known limitations / hardening backlog

- In-memory rate limiter is per-process; use Redis for multi-worker/multi-node.
- Image/vision send path is not yet wired (model vision capability is surfaced but image upload is intentionally disabled to avoid faking unsupported behavior).
- Consider adding account email verification and 2FA for higher-assurance deployments.
