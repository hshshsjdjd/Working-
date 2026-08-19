# Implementation status

Per-area status against the build specification. "Done" means implemented with
real (non-mock) backend integration. Where something is intentionally scoped as
a follow-up, it is called out explicitly rather than faked.

| # | Area | Status | Notes |
| - | ---- | ------ | ----- |
| 1 | Core architecture (browser → HTTPS → proxy → SPA → backend → NVIDIA) | Done | Key never reaches the browser. |
| 2 | Tech stack (React/TS/Vite/Tailwind, FastAPI/HTTPX/Pydantic, Postgres, Docker/Caddy) | Done | |
| 3 | Main chat UI (AMOLED, mobile-first, responsive) | Done | |
| 4 | Chat features (new/send/stop/regenerate/edit/copy/markdown/code/tables/streaming/auto-scroll/timestamps) | Done | "Retry" == regenerate. |
| 5 | Model selector (name/id/capabilities/availability/selection, configurable) | Done | Server-side catalog + admin toggles. |
| 6 | NVIDIA API (auth, chat completions, streaming, switching, timeout, retry, rate-limit, errors, cancellation) | Done | OpenAI-compatible `/chat/completions`. |
| 7 | Streaming + stop (preserve partial) | Done | Partial text persisted on stop/disconnect. |
| 8 | Conversations (new/rename/delete/search/pin/archive/export) + per-user | Done | Import: export is JSON; re-import UI not included. |
| 9 | Accounts (register/login/logout/profile/change-password/delete) | Done | |
| 10 | User isolation (server-side identity, no trust of client IDs) | Done | Tested (IDOR). |
| 11 | Coding mode | Partial | Code generation/highlighting/copy work for any prompt; no separate mode toggle UI. |
| 12 | File upload (picker/progress/preview/delete/attach, validation, traversal/exec prevention, per-user) | Done (text) | Text files injected as context; validation + per-user storage tested. |
| 13 | Image/vision support | Not wired | Vision capability is surfaced in the model list; image send path intentionally disabled to avoid faking unsupported behavior. |
| 14 | Settings (appearance/AI/chat/account) | Done | |
| 15 | Custom system prompt (per user + per conversation) | Done | |
| 16 | Context management (preserve system + recent, keep current request) | Done | Token-budget trimming. |
| 17 | Security (SQLi/XSS/CSRF/SSRF/IDOR/authz/brute-force/uploads/traversal/oversized) | Done | See `SECURITY.md`. |
| 18 | API-key security (never in client/logs/responses) | Done | Tested. |
| 19 | Rate limiting (/login /register /chat /upload, 429) | Done | Configurable; in-memory (Redis for scale). |
| 20 | Database (all tables, migrations, indexes, parameterized) | Done | Alembic + SQLAlchemy. |
| 21 | Usage tracking (requests/model/timestamp/latency/success/tokens) + page | Done | Only real tokens counted. |
| 22 | Admin panel (stats, model toggles, disable accounts, maintenance, RBAC) | Done | |
| 23 | PWA (manifest/service worker/icons/standalone/offline) | Done | Offline never fakes AI. |
| 24 | Responsive design (mobile/tablet/desktop, touch/mouse/keyboard) | Done | |
| 25 | Performance (code output streamed, no polling, caching where safe) | Done | Bundle could be code-split further. |
| 26 | Error handling (friendly, no stack traces) | Done | |
| 27 | Logging (structured, no secrets) | Done | JSON logs + redaction. |
| 28 | Health endpoints (/health, /ready) | Done | |
| 29 | API routes | Done | See `backend/app/routers`. |
| 30 | Docker deployment (compose: frontend/backend/postgres/reverse-proxy) | Done | Postgres not published. |
| 31 | HTTPS (Caddy, redirect, minimal ports) | Done | Auto-HTTPS with a domain. |
| 32 | Domain (no backend ports exposed) | Done | |
| 33 | Environment configuration (.env.example) | Done | |
| 34 | Backup docs | Done | `docs/BACKUP.md`. |
| 35 | Tests (auth/authz/ownership/NVIDIA/streaming/models/uploads/rate-limit/XSS/traversal/key) | Done | `backend/tests` (pytest). |
| 36 | Security review | Done | `docs/SECURITY.md`. |
| 37 | No mock implementation in product | Done | Real integration; a mock server exists only under `scripts/` for dev/testing and is never deployed. |
| 38 | UI quality (empty state, sidebar, selector, composer, streaming, stop, copy, code toolbar, toasts, settings/account UI) | Done | Loading skeletons are minimal (spinners). |
| 39 | Final files (frontend/backend/compose/Dockerfiles/proxy/migrations/.env.example/README/tests/docs/PWA) | Done | |
| 40 | Deployment guide | Done | `docs/DEPLOYMENT.md`. |

## Intentional follow-ups

- **Image/vision** send path (section 13) and **conversation import** (section 8) are not implemented; everything else is functional.
- **Coding mode** (section 11) is available implicitly (code prompts render with highlighting and copy) but has no dedicated mode switch.
- Rate limiting is in-memory; use Redis for multi-worker/multi-node scale.
