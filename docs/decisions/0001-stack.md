# 1. FastAPI + React instead of Rails

Date: 2026-10-22 · Status: accepted

## Context

The author's background is Rails. The project has two goals: a useful family expense tracker, and a portfolio piece aimed at Python / AI engineering roles. Later phases are AI-heavy: receipt extraction with vision models, LLM categorization with evals, natural-language queries over the data, an MCP server.

## Decision

- **Backend: FastAPI (Python).** Python is where the AI ecosystem lives, and FastAPI is the common choice for AI-backed product APIs. Pydantic models give validation and the OpenAPI schema for free.
- **Not Rails:** it would be the fastest path, but it adds nothing new to the portfolio, and keeping Rails as a "skeleton" next to a Python service would mean two backends for one product.
- **Not Django:** closer to Rails and batteries-included, but FastAPI is more aligned with AI roles and keeps the stack small.
- **Frontend: React + TypeScript with Vite**, the industry default. Kept deliberately conventional: TanStack Query for server state, Tailwind for styling, no meta-framework (Next.js) until there is a need.
- **Sync SQLAlchemy** (not async) for now: simpler to read and test; FastAPI runs sync endpoints in a thread pool. LLM calls can be made async independently when they arrive.

## Consequences

- The frontend will consume the API through a TypeScript client generated from FastAPI's OpenAPI schema, so the backend stays the single source of truth for types.
- Two toolchains (uv and npm) to maintain, both pinned (`uv.lock`, `package-lock.json`, `.python-version`, `.nvmrc`).
