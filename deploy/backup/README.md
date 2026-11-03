# Database backups

- **Server**: `family-finances-backup.timer` runs `backup.sh` every day at 03:15 UTC.
  Backups go to `/var/backups/family-finances` (last 7 days, root-only).
- **Mac**: launchd agent `com.family-finances.backup-pull` runs `pull.sh` every day at 10:15
  (or on wake if the Mac was asleep). Backups go to `~/Backups/family-finances` (last 7 days).
  If the newest one is older than 48 hours, or the server can't be reached, it shows a macOS
  notification. Log: `/tmp/family-finances-backup-pull.log`.

Backups contain real financial data: never copy them into the repo.

## Restore

On the server:

```sh
cd /opt/family-finances
ls -lt /var/backups/family-finances
deploy/backup/restore.sh /var/backups/family-finances/family_finances_YYYYMMDD_HHMMSS.sql.gz
```

To restore from a Mac copy, upload it first:

```sh
scp ~/Backups/family-finances/family_finances_YYYYMMDD_HHMMSS.sql.gz digitalocean:/var/backups/family-finances/
```

## Install

Server:

```sh
cp deploy/backup/family-finances-backup.{service,timer} /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now family-finances-backup.timer
```

Mac:

```sh
cp deploy/backup/com.family-finances.backup-pull.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.family-finances.backup-pull.plist
```
