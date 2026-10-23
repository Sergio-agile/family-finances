# Working agreement

- Claude writes the code; Sergio reviews it. Optimize every change for reviewability: small PRs, one new concept per PR when possible.
- Sergio comes from Rails. When a PR introduces a new Python/FastAPI or React concept, add it to `docs/learning/rails-to-fastapi.md` with the Rails equivalent, plus 1–2 review questions. Learning notes are in Spanish; code, README and ADRs in English.
- Record significant technical decisions as ADRs in `docs/decisions/`.
- Never push to `main`: one branch per change, opened as a PR.

# Safety

- The repo is public. Never commit `.env`, API keys, or real financial data (bank exports, real movements). Demo data must be invented.

# Gotchas

- Postgres runs on host port **5434** (5432 is a local Postgres, 5433 is another project's container).
- Node 22 via nvm (`.nvmrc`); the machine's default Node is 16, so run `nvm use` before npm commands.
- macOS 12 is unsupported by Homebrew: don't install tools with `brew` (it builds from source and can break openssl for other projects). Use official standalone installers.
- Disk space on the dev machine is tight; prefer the existing Python 3.12 over downloading interpreters (`UV_PYTHON_DOWNLOADS=never`).
