#!/usr/bin/env bash
#
# Cloud Agent environment INSTALL script.
#
# Installs system packages, Python + Node dependencies, builds the frontend,
# provisions PostgreSQL, and applies migrations + model seed. Idempotent: safe
# to run repeatedly and against a warm/snapshotted filesystem.
#
# Secrets (NVIDIA_API_KEY, etc.) are NOT referenced here — the backend reads
# them from the secure runtime environment at start time.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

echo "==> [1/6] Installing system packages (postgresql, python3-venv)"
export DEBIAN_FRONTEND=noninteractive
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
  postgresql postgresql-contrib python3-venv

echo "==> [2/6] Starting PostgreSQL"
$SUDO service postgresql start

echo "==> [3/6] Ensuring database role and database exist"
$SUDO -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='nvidia'" | grep -q 1 \
  || $SUDO -u postgres psql -c "CREATE ROLE nvidia LOGIN PASSWORD 'nvidia';"
$SUDO -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='nvidia_ai'" | grep -q 1 \
  || $SUDO -u postgres createdb -O nvidia nvidia_ai
# Test database for the pytest suite.
$SUDO -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='nvidia_ai_test'" | grep -q 1 \
  || $SUDO -u postgres createdb -O nvidia nvidia_ai_test

echo "==> [4/6] Backend: virtualenv + dependencies"
cd "$ROOT/backend"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements-dev.txt

echo "==> [5/6] Backend: migrations + model seed"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://nvidia:nvidia@127.0.0.1:5432/nvidia_ai}"
export SECRET_KEY="${SECRET_KEY:-dev-environment-secret}"
./.venv/bin/alembic upgrade head
./.venv/bin/python -m scripts.seed

echo "==> [6/6] Frontend: install dependencies + production build"
cd "$ROOT/frontend"
npm ci
npm run build

echo "==> Install complete."
