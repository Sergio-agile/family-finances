# 11. Daily database backups, on the server and on the Mac

Date: 2026-11-03 · Status: accepted

## Context

The app is in production (ADR 0010) and about to hold the family's real financial data. Its Postgres runs in a container on a single server: a broken volume, a bad migration or a lost server would lose everything. easy-admin, on the same server, already has a backup routine that works.

## Decision

- **Same routine as easy-admin**, so both apps are operated the same way: a systemd timer runs `pg_dump` every day (`--clean --if-exists --no-owner`, gzipped), and the files live in `/var/backups/family-finances` (root-only) for 7 days.
- **A second copy off the server**: a launchd agent on the Mac pulls new files every day with `rsync` and keeps 7 days in `~/Backups/family-finances`.
- **Failures are noisy**: the Mac shows a notification if the server can't be reached or the newest backup is older than 48 hours, so a backup that silently stopped is noticed within two days.
- The dump is written to a temporary file and renamed at the end, so a failed dump never looks like a backup.
- **Restore** stops the app, loads the dump with `psql -v ON_ERROR_STOP=1` and starts the app again, after typing `restore` to confirm.
- 03:15, not 03:00, so it doesn't run at the same time as easy-admin's on a 1 GB server.

## Alternatives considered

- **DigitalOcean droplet backups/snapshots:** whole-server images, weekly, paid, and restoring one rolls back easy-admin too. Useful as an extra layer, not as the database backup.
- **Managed Postgres:** backups and point-in-time recovery included, but it costs more than the whole server for a family app.
- **Off-site object storage (S3, Spaces):** survives losing both server and Mac, but needs credentials on the server and client-side encryption. Worth revisiting if the Mac copy isn't enough.
- **Sharing the scripts with easy-admin in Sergio-agile/infra:** less duplication, but each app's backup would depend on another repo. Two small copies of the same pattern are easier to follow.

## Consequences

- Up to 24 hours of data can be lost (the time since the last dump). For a family's expenses, acceptable.
- Backups are not encrypted at rest: they rely on root-only permissions on the server and FileVault on the Mac.
- A restore is only proven by doing one: the first one was rehearsed into a scratch database right after installing.
