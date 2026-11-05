# 10. Deploy with Docker Compose behind the server's shared Caddy

Date: 2026-11-03 · Status: accepted

## Context

The app goes to production on a small self-managed server (1 vCPU, 1 GB RAM) that already runs easy-admin. Only one process can listen on ports 80/443, so the server has a single Caddy reverse proxy for every app, in its own repo (Sergio-agile/infra). The deploy must be cheap in memory, simple to repeat by hand, and keep the guarantees of ADRs 0004, 0008 and 0009 (Host header, client IP, security headers).

## Decision

- **One image for API and frontend**, built in three stages: Node builds the frontend, uv installs the Python dependencies, and the final `python:3.12-slim` image holds only the virtualenv, the app code and `frontend/dist`, served by FastAPI (PR 23). No Node at runtime; the image runs as an unprivileged user.
- **`docker-compose.prod.yml`** with the app and its **own Postgres 17**, not shared with easy-admin: separate backups, versions and failures for ~30 MB of RAM. Both get `mem_limit: 256m`.
- **No published ports.** The app joins the external `proxy` network with the alias `family-finances` (easy-admin also has a service called `web`). Its site block lives here in `deploy/caddy/`, mounted and imported by the shared Caddy.
- **Migrations run on every start** (`alembic upgrade head`), then `fastapi run` with **one worker**. *Updated 2026-11-05 (PR 29): both now run in one Python process, `python -m app.serve`, which imports the app once instead of twice; see Consequences.*
- **Client IP:** `--proxy-headers --forwarded-allow-ips '*'`. Trusting any forwarder is safe only because nothing but Caddy can reach the container, and Caddy overwrites the `X-Forwarded-For` a client sends. Without it, every request would seem to come from Caddy, and the per-IP throttle (ADR 0008) would lock out the whole family at once.
- **Host header:** Caddy forwards the client's `Host` unchanged, which the Origin check (ADR 0004) and `ALLOWED_HOSTS` (ADR 0009) rely on.
- **Configuration:** the server's `.env.production` holds only `POSTGRES_PASSWORD` and `FAMILY_FINANCES_DOMAIN`. The compose file derives `DATABASE_URL`, `APP_URL` and `ALLOWED_HOSTS`, and hardcodes `ENVIRONMENT=production`, so the unsafe-settings check (ADR 0009) can't be bypassed by a missing variable.
- **The image is built on the server** (`up -d --build`), like easy-admin.

## Alternatives considered

- **Caddy serving `frontend/dist` from a host directory:** fastest for static files, but frontend and API would be deployed separately, and a rebuild leaves the directory empty for a moment.
- **Sharing easy-admin's Postgres:** saves ~30 MB, but couples upgrades, backups and outages of two unrelated apps.
- **Building images in CI and pulling them from a registry:** faster deploys and no build load on the server, but it needs a registry and credentials. Worth it if builds on the server start to hurt.
- **Several workers:** more throughput than a family needs, and each one is another ~80 MB.

## Consequences

- Deploying is `git pull` + `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build` in `/opt/family-finances`, with the proxy stack already running.
- Downtime per deploy while the new container starts. Measured at ~27 s with Alembic and the `fastapi` CLI as two processes: importing the app takes ~5 s on this server, and it was paid twice. Stopping the old container takes ~1.5 s. PR 29 merges both steps into one process. Acceptable for a family app; zero downtime would need two app containers behind Caddy, not worth it on 1 GB.
- A migration that fails stops the app from starting, so the old schema is never served by new code.
- Backups are not part of this decision; they come in the next PR, before real data goes in.
