# Production image: API + built frontend in one container (ADR 0010).
#   docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 1. Build the frontend. Only dist/ leaves this stage: no Node in the final image.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. Install the Python dependencies with uv. Only the virtualenv leaves this stage.
FROM python:3.12-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev

# 3. Runtime: Python, the virtualenv, the app code and the frontend build.
FROM python:3.12-slim
RUN useradd --system --no-create-home app
WORKDIR /app
COPY --from=backend /app/.venv .venv
COPY backend/alembic.ini ./
COPY backend/migrations migrations
COPY backend/app app
COPY --from=frontend /frontend/dist frontend-dist
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 FRONTEND_DIST=/app/frontend-dist
USER app
EXPOSE 8000
# Migrate, then serve. One worker: a family's traffic, 1 GB of RAM on the server.
# --proxy-headers: the client IP comes from Caddy's X-Forwarded-For (login throttling, ADR 0008).
# Any forwarder is trusted because no port is published: only Caddy, on the proxy network, can
# reach this container, and Caddy replaces any X-Forwarded-For a client sends.
CMD ["sh", "-c", "alembic upgrade head && exec fastapi run app/main.py --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
