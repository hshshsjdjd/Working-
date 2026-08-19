#!/usr/bin/env bash
#
# Cloud Agent environment START script.
#
# Starts PostgreSQL, applies migrations (idempotent), launches the FastAPI
# backend on :8000, and runs the frontend dev server on :5173 (which proxies
# /api and /health to the backend). Stays attached via the frontend process.
#
# NVIDIA_API_KEY is inherited from the secure runtime environment (Cursor
# Secrets) — it is never hardcoded, printed, or written to disk here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://nvidia:nvidia@127.0.0.1:5432/nvidia_ai}"
export SECRET_KEY="${SECRET_KEY:-dev-environment-secret}"
export APP_ENV="${APP_ENV:-development}"
export COOKIE_SECURE="${COOKIE_SECURE:-false}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173}"
export NVIDIA_BASE_URL="${NVIDIA_BASE_URL:-https://integrate.api.nvidia.com/v1}"
export UPLOAD_DIR="${UPLOAD_DIR:-$ROOT/.data/uploads}"
mkdir -p "$UPLOAD_DIR" "$ROOT/.data"

echo "==> Starting PostgreSQL"
$SUDO service postgresql start || true
for _ in $(seq 1 30); do
  if $SUDO -u postgres psql -tAc "SELECT 1" >/dev/null 2>&1; then break; fi
  sleep 1
done

echo "==> Applying migrations + seed"
cd "$ROOT/backend"
./.venv/bin/alembic upgrade head
./.venv/bin/python -m scripts.seed

echo "==> Starting backend API on :8000 (logs -> .data/backend.log)"
nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips "*" \
  > "$ROOT/.data/backend.log" 2>&1 &

echo "==> Starting frontend on :5173 (proxies /api to the backend)"
cd "$ROOT/frontend"
exec npm run dev -- --host --port 5173
