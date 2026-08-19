# Backup & restore

The durable state is the PostgreSQL database and the uploads volume.

## Database backup

Create a compressed logical backup (custom format):

```bash
docker compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > backup_$(date +%F_%H%M).dump
```

Plain SQL alternative:

```bash
docker compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > backup_$(date +%F).sql.gz
```

## Database restore

Restore a custom-format dump into a running database:

```bash
cat backup_2026-01-01_1200.dump | docker compose exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
```

Restore a gzipped SQL dump:

```bash
gunzip -c backup_2026-01-01.sql.gz | docker compose exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

## Uploaded files

Back up the uploads volume:

```bash
docker run --rm -v nvidia-ai_uploads:/data -v "$PWD":/backup alpine \
  tar czf /backup/uploads_$(date +%F).tar.gz -C /data .
```

Restore:

```bash
docker run --rm -v nvidia-ai_uploads:/data -v "$PWD":/backup alpine \
  sh -c "cd /data && tar xzf /backup/uploads_YYYY-MM-DD.tar.gz"
```

(The volume name is `<project>_uploads`; check with `docker volume ls`.)

## Scheduled backups (recommended)

Add a root cron entry to back up nightly and keep 14 days:

```cron
0 3 * * * cd /opt/nvidia-ai && docker compose exec -T postgres pg_dump -U nvidia -Fc nvidia_ai > /var/backups/nvidia-ai/db_$(date +\%F).dump 2>>/var/log/nvidia-ai-backup.log && find /var/backups/nvidia-ai -name 'db_*.dump' -mtime +14 -delete
```

## Safety

- Store backups off-box (e.g. encrypted object storage) and restrict access.
- Backups contain user data — never expose the backup directory publicly.
- Test restores periodically on a staging database.
