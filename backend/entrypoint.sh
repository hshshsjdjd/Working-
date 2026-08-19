#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for the database…"
python - <<'PY'
import time
import sqlalchemy
from app.config import settings

engine = sqlalchemy.create_engine(settings.database_url)
for attempt in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        print("Database is ready.")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"  db not ready ({attempt+1}/60): {exc}")
        time.sleep(2)
else:
    raise SystemExit("Database did not become ready in time")
PY

echo "Applying migrations…"
alembic upgrade head

echo "Seeding model catalog…"
python -m scripts.seed

# Single worker keeps the in-memory rate limiter consistent. For multi-worker
# horizontal scaling, back the limiter with Redis (see README).
echo "Starting API…"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips "*"
