# Family Finances

A family expense tracker: log expenses from your phone, import bank movements, and let AI do the boring parts (receipt scanning, categorization, answering questions about your spending).

Built as a portfolio project with a Python/FastAPI backend and a React/TypeScript frontend.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2, PostgreSQL, managed with [uv](https://docs.astral.sh/uv/)
- **Frontend:** React + TypeScript, Vite, TanStack Query, Tailwind CSS
- **Automation:** webhooks for n8n / Make
- **CI:** GitHub Actions (lint, format, tests, build)

Why these choices: see [docs/decisions](docs/decisions).

## Running locally

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 22 (`.nvmrc`).

```sh
cp .env.example .env
docker compose up -d          # Postgres on localhost:5434

cd backend
uv sync
uv run fastapi dev app/main.py   # http://localhost:8000/docs

cd ../frontend
npm install
npm run dev                      # http://localhost:5173
```

Backend tests: `cd backend && uv run pytest` (needs the database running).

## Roadmap

1. Expenses: add and list expenses, categories
2. Auth and shared family accounts
3. Webhooks + n8n (expenses → Google Sheets, weekly summary)
4. Bank CSV import and reconciliation, LLM auto-categorization with evals
5. Receipt photo → expense
6. Bank sync via PSD2
7. Ask your finances in natural language, MCP server
8. Public demo deployment
