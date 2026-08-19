# NVIDIA AI — Web Chat Application

A production-oriented, web-based chat application for NVIDIA AI models. It runs
entirely in a normal browser (Chrome, Firefox, Edge, Safari — desktop and
mobile). No Termux, Android Studio, or native app is required — users just open
the site URL.

The NVIDIA API key **never** touches the browser. All model traffic flows
through a secure backend:

```
Browser  →  HTTPS  →  Reverse proxy (Caddy)  →  React SPA  +  FastAPI backend  →  NVIDIA API
```

## Tech stack

| Layer     | Technology |
| --------- | ---------- |
| Frontend  | React, TypeScript, Vite, Tailwind CSS, PWA |
| Backend   | Python, FastAPI, HTTPX, Pydantic, SQLAlchemy |
| Database  | PostgreSQL (Alembic migrations) |
| Auth      | HTTP-only session cookies, double-submit CSRF, Argon2id hashing |
| Deploy    | Docker, Docker Compose, Caddy (auto-HTTPS) |

## Features

- **Streaming chat** with real-time token streaming, **Stop**, **Regenerate**, **Edit**, **Copy** (message and code blocks), Markdown, syntax-highlighted code, tables, and lists.
- **Conversations**: create, rename, delete, search, pin, archive, export (JSON). Each conversation belongs to exactly one user.
- **Model selector** driven by a server-side catalog of **real** NVIDIA NIM model IDs (never invented). Admins can enable/disable models.
- **Accounts**: register, login, logout, change password, delete account. The first registered user becomes an admin.
- **Settings**: appearance (Dark / Light / System / **AMOLED**), AI parameters (model, temperature, top-p, max tokens, custom system prompt), and chat toggles.
- **File attachments**: upload validated text files (`.txt`, `.md`, `.csv`, `.json`) and attach them as prompt context.
- **Usage tracking**: requests, success/failure, latency, and real token totals (only counts NVIDIA actually returns — never fabricated).
- **Admin dashboard**: user/request stats, model toggles, maintenance mode, audit log, DB status.
- **PWA**: installable, standalone display, offline banner (AI requests always require the network — never faked offline).
- **Security**: parameterized queries, strict CORS, security headers/CSP, CSRF protection, rate limiting, upload validation, IDOR-safe ownership checks, and no secret exposure/logging.

See [`docs/STATUS.md`](docs/STATUS.md) for a precise per-requirement implementation status, including the parts that are intentionally scoped as follow-ups (e.g. image/vision send path).

## Repository layout

```
backend/     FastAPI app, migrations, tests, Dockerfile
frontend/    React + Vite SPA, Dockerfile, nginx config
Caddyfile    Reverse proxy + HTTPS
docker-compose.yml
.env.example
docs/        Deployment, backup, security, status
```

## Quick start (Docker — recommended)

1. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env:
   #   SECRET_KEY=$(openssl rand -hex 32)
   #   POSTGRES_PASSWORD=<a strong password>
   #   DATABASE_URL=postgresql+psycopg://nvidia:<same password>@postgres:5432/nvidia_ai
   #   NVIDIA_API_KEY=<your key from build.nvidia.com>
   #   CORS_ORIGINS=http://localhost      (or https://yourdomain.com)
   #   SITE_ADDRESS=:80                    (or yourdomain.com for auto-HTTPS)
   ```

2. **Build and run**

   ```bash
   docker compose up -d --build
   ```

   Migrations run automatically and the model catalog is seeded on start.

3. **Open** `http://localhost` (or your domain). The first account you register
   becomes the admin.

To create/promote an admin explicitly:

```bash
docker compose exec backend python -m scripts.create_admin you@example.com 'your-strong-password'
```

## Local development (without Docker)

Prerequisites: Python 3.12+, Node 20+, a running PostgreSQL.

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql+psycopg://nvidia:nvidia@127.0.0.1:5432/nvidia_ai"
export SECRET_KEY="dev-secret"
export NVIDIA_API_KEY="<your key>"
export APP_ENV=development COOKIE_SECURE=false
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 (proxies /api to :8000)
```

**Run the tests**

```bash
cd backend && source .venv/bin/activate
export DATABASE_URL="postgresql+psycopg://nvidia:nvidia@127.0.0.1:5432/nvidia_ai_test"
python -m pytest
```

### Trying the streaming pipeline without a real key

A dev-only OpenAI-compatible mock server is included (never deployed):

```bash
cd backend && source .venv/bin/activate
python -m scripts.mock_nvidia_server           # listens on :9999
# In the backend shell:
export NVIDIA_BASE_URL="http://localhost:9999/v1"
export NVIDIA_API_KEY="dev-key"
uvicorn app.main:app --reload --port 8000
```

## Deployment, backups, security

- Deployment to a Linux VPS + domain + HTTPS: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- Database backup/restore: [`docs/BACKUP.md`](docs/BACKUP.md)
- Security model and review checklist: [`docs/SECURITY.md`](docs/SECURITY.md)

## Configuration reference

All configuration is via environment variables — see [`.env.example`](.env.example)
for the full list with defaults. Secrets (`NVIDIA_API_KEY`, `SECRET_KEY`,
`DATABASE_URL`) are read only on the server and are never exposed to the client
or logged.
