# Deployment guide

End-to-end steps to run the NVIDIA AI application in production on a Linux VPS
with a domain and automatic HTTPS.

## 1. Prerequisites

- A Linux VPS (Ubuntu 22.04/24.04 recommended), 1 vCPU / 1–2 GB RAM minimum.
- A domain name with an `A`/`AAAA` DNS record pointing at the VPS public IP.
- An NVIDIA API key from <https://build.nvidia.com> (used server-side only).
- Docker Engine + Docker Compose plugin installed.

Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # log out/in afterwards
```

## 2. Get the code

```bash
git clone <your-repo-url> nvidia-ai && cd nvidia-ai
```

## 3. Configure

```bash
cp .env.example .env
```

Set at minimum:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | output of `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | a strong password |
| `DATABASE_URL` | `postgresql+psycopg://nvidia:<password>@postgres:5432/nvidia_ai` |
| `NVIDIA_API_KEY` | your NVIDIA key |
| `CORS_ORIGINS` | `https://yourdomain.com` |
| `SITE_ADDRESS` | `yourdomain.com` (enables automatic HTTPS) |

`SITE_ADDRESS=yourdomain.com` makes Caddy obtain and renew a Let's Encrypt
certificate automatically. Use `:80` only for local/plain-HTTP testing.

## 4. Open the firewall

```bash
sudo ufw allow 80,443/tcp && sudo ufw enable
```

Only 80/443 are exposed. PostgreSQL and the backend/frontend containers are on
an internal Docker network and are never published publicly.

## 5. Build and start

```bash
docker compose up -d --build
```

The backend waits for PostgreSQL, applies migrations, seeds the model catalog,
and starts. Watch logs with `docker compose logs -f`.

## 6. Verify

```bash
curl -fsS https://yourdomain.com/health     # {"status":"ok"}
curl -fsS https://yourdomain.com/ready       # database + nvidia_configured flags
```

Open `https://yourdomain.com` in a browser.

## 7. Create the first admin

The first account registered through the UI is automatically an admin. To do it
explicitly or reset it:

```bash
docker compose exec backend python -m scripts.create_admin you@example.com 'strong-password'
```

## 8. Test NVIDIA connectivity

1. Sign in, pick a model in the selector, send a message.
2. The response should stream token-by-token.
3. If you see "The NVIDIA API is not configured", set `NVIDIA_API_KEY` and
   `docker compose up -d` again. If you see "invalid API key", re-check the key.

## 9. Updating the application

```bash
git pull
docker compose up -d --build     # migrations run automatically on backend start
```

## 10. Install as an app (PWA)

On mobile Chrome/Safari or desktop Chrome/Edge, use "Add to Home Screen" /
"Install app". The app runs standalone; when offline it shows a banner and never
pretends the AI works without a connection.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `SECRET_KEY`/`POSTGRES_PASSWORD` compose error | Values are required in `.env`. |
| TLS certificate not issued | Ensure DNS points to the VPS and ports 80/443 are open; check `docker compose logs reverse-proxy`. |
| 502 on `/api/*` | Backend not healthy — `docker compose logs backend`. |
| "invalid API key" in chat | Fix `NVIDIA_API_KEY`, then `docker compose up -d`. |
| DB connection errors | Confirm `DATABASE_URL` host is `postgres` and the password matches `POSTGRES_PASSWORD`. |
| Rate-limit 429s under load with many workers | The limiter is in-memory/per-process; back it with Redis for horizontal scaling. |

## Scaling notes

- The default backend runs a single Uvicorn worker so the in-memory rate limiter
  is consistent. To scale out, move rate limiting and sessions coordination to
  Redis and increase workers/replicas.
- Uploaded files are stored on the `uploads` Docker volume (per-user
  subdirectories). For multi-node deployments use shared/object storage.
