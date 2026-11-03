#!/bin/bash
# Runs on the server (systemd timer): dumps the production database and keeps the last 7 days.
set -euo pipefail

APP_DIR=${APP_DIR:-/opt/family-finances}
BACKUP_DIR=${BACKUP_DIR:-/var/backups/family-finances}
KEEP_DAYS=${KEEP_DAYS:-7}

cd "$APP_DIR"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

file="$BACKUP_DIR/family_finances_$(date +%Y%m%d_%H%M%S).sql.gz"

# Written to .tmp and renamed at the end, so a failed dump never looks like a backup.
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T db \
  pg_dump -U family -d family_finances --clean --if-exists --no-owner \
  | gzip > "$file.tmp"
mv "$file.tmp" "$file"
chmod 600 "$file"

find "$BACKUP_DIR" -name 'family_finances_*.sql.gz' -mtime +$((KEEP_DAYS - 1)) -delete

echo "Backup created: $file ($(du -h "$file" | cut -f1))"
