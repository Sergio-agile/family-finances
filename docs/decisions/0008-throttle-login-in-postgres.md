# 8. Throttle login and sign-up failures in Postgres

Date: 2026-11-02 · Status: accepted

## Context

Before going to production, nothing limited how many passwords someone could try. Argon2 makes each guess cost ~50 ms of server time, but that only slows an attacker down; it doesn't stop one. Invitation tokens are 256-bit random values and can't be guessed, but repeated bad sign-ups are still worth limiting.

## Decision

- Every failed login and every sign-up with an invalid invitation is stored in an **`auth_failures`** table (email, client IP, time).
- Before checking a password, the API counts recent failures. **More than 5 for the email, or 20 for the IP, in the last 15 minutes → `429 Too Many Requests`** with `Retry-After: 900`. Since the password isn't checked while throttled, a lucky guess goes unnoticed and costs no Argon2.
- A successful login clears that email's failures, so a family member who mistyped a few times starts again from zero.
- Rows older than the window are deleted whenever a new failure is stored, so the table stays small.
- Sign-up checks the invitation **before** the email, so without a valid invitation nobody can find out whether an email has an account.

## Alternatives considered

- **slowapi (in-memory limits):** the usual FastAPI library. Counts live in the process: they reset on every restart and aren't shared between several worker processes. Making it shared needs Redis, an extra service to run.
- **Only at the reverse proxy (nginx `limit_req`, Caddy):** good against floods, and worth adding at deploy time too. But a proxy can't see the email inside the request body, so it can't protect one account against slow guessing from many addresses.
- **Lock the account until an admin unlocks it:** stronger, but anyone knowing an email could lock that person out indefinitely.

## Consequences

- Anyone who knows a member's email can block that member's login for up to 15 minutes by failing on purpose. This is the usual trade-off of per-account limits, and the block is short.
- Each login does up to two extra indexed counts (`(email, created_at)` and `(ip, created_at)`).
- **Deploy requirement:** behind a reverse proxy, run uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy address>`. Otherwise every request appears to come from the proxy, and the per-IP limit becomes one limit shared by the whole world.
- Several family members behind the same home router share the per-IP budget (20 failures every 15 minutes), which is plenty for typos.
