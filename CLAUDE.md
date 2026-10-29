# Working agreement

- Claude writes the code; Sergio reviews it. Optimize every change for reviewability: small PRs, one new concept per PR when possible.
- Sergio comes from Rails. When a PR introduces a new Python/FastAPI or React concept, add it to `docs/learning/rails-to-fastapi.md` with the Rails equivalent, plus 1–2 review questions. Learning notes are in Spanish; code, README and ADRs in English.
- Record significant technical decisions as ADRs in `docs/decisions/`.
- Never push to `main`: one branch per change, opened as a PR.

# Engineering principles

Non-negotiable for every change, backend and frontend:

- **Conventions first.** Follow the idiomatic, senior-level conventions of each tool (FastAPI, SQLAlchemy 2.0, Pydantic v2, React, TanStack Query, Tailwind) before inventing anything. If a decision departs from convention, justify it in an ADR.
- **Reuse before writing.** Look for an existing helper, component, fixture or pattern and extend it; extract shared code as soon as something repeats. No copy-paste.
- **Performance is a feature.** Keep it as light as possible:
  - Backend: no N+1 (eager-load relationships), index what we filter or join on, paginate or bound lists, push aggregation into SQL instead of Python.
  - Frontend: few and small dependencies, watch the bundle size, cache server state with TanStack Query instead of refetching, avoid needless re-renders and `useEffect`.
- **Optimized, minimal code.** The simplest correct solution with the fewest moving parts; no speculative abstractions.
- In every PR description, call out any performance impact (new queries, indexes, bundle size).

# Safety

- The repo is public. Never commit `.env`, API keys, or real financial data (bank exports, real movements). Demo data must be invented.

# Gotchas

- After changing any endpoint or Pydantic schema, run `npm run gen:api` in `frontend/` and commit the regenerated `openapi.json` and `src/api/generated/` (never edit generated files by hand).

- Postgres runs on host port **5434** (5432 is a local Postgres, 5433 is another project's container).
- Node 22 via nvm (`.nvmrc`); the machine's default Node is 16, so run `nvm use` before npm commands.
- macOS 12 is unsupported by Homebrew: don't install tools with `brew` (it builds from source and can break openssl for other projects). Use official standalone installers.
- Disk space on the dev machine is tight; prefer the existing Python 3.12 over downloading interpreters (`UV_PYTHON_DOWNLOADS=never`).
