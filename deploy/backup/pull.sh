#!/bin/bash
# Runs on the Mac (launchd): copies new server backups locally, keeps the last 7 days, and warns
# with a macOS notification if the newest backup is too old (the server job may be failing).
set -euo pipefail

SERVER=${SERVER:-digitalocean}
REMOTE_DIR=${REMOTE_DIR:-/var/backups/family-finances}
LOCAL_DIR=${LOCAL_DIR:-$HOME/Backups/family-finances}
KEEP_DAYS=${KEEP_DAYS:-7}
MAX_AGE_HOURS=${MAX_AGE_HOURS:-48}

warn() {
  echo "$(date '+%F %T') WARNING: $1"
  osascript -e "display notification \"$1\" with title \"family-finances backups\"" || true
  exit 1
}

mkdir -p "$LOCAL_DIR"
chmod 700 "$LOCAL_DIR"

rsync -a --ignore-existing -e "ssh -o BatchMode=yes" "$SERVER:$REMOTE_DIR/" "$LOCAL_DIR/" \
  || warn "Could not copy backups from the server"

find "$LOCAL_DIR" -name 'family_finances_*.sql.gz' -mtime +$((KEEP_DAYS - 1)) -delete

recent=$(find "$LOCAL_DIR" -name 'family_finances_*.sql.gz' -mmin -$((MAX_AGE_HOURS * 60)))
[ -n "$recent" ] || warn "No backup newer than $MAX_AGE_HOURS hours"

echo "$(date '+%F %T') Backups in $LOCAL_DIR: $(ls "$LOCAL_DIR" | wc -l | tr -d ' ')"
