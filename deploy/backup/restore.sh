#!/bin/bash
# Runs on the server: restores the production database from a backup file.
# Usage: deploy/backup/restore.sh /var/backups/family-finances/family_finances_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail

file=${1:?Usage: $0 <backup.sql.gz>}
APP_DIR=${APP_DIR:-/opt/family-finances}

[ -f "$file" ] || { echo "File not found: $file"; exit 1; }
gzip -t "$file"

cd "$APP_DIR"
compose() { docker compose -f docker-compose.prod.yml --env-file .env.production "$@"; }

read -r -p "This will REPLACE the production database with $file. Type 'restore' to continue: " answer
[ "$answer" = "restore" ] || { echo "Aborted"; exit 1; }

# The app is stopped so nobody writes while the data is replaced.
compose stop web
gunzip -c "$file" | compose exec -T db psql -U family -d family_finances -v ON_ERROR_STOP=1 -q
compose start web

echo "Database restored from $file"
