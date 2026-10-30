# 4. Accounts with email + password and server-side sessions

Date: 2026-10-30 · Status: accepted

## Context

The app will hold a family's real spending and will be deployed publicly, so every data endpoint needs a logged-in user. Users are a handful of family members, and later perhaps other families. The browser frontend and the API share one origin. Machine clients (n8n, bank sync) will come later with their own scoped tokens.

We do not want to depend on Google or another identity provider with the family's data, and there is no email service yet.

## Decision

- **Email + password.** Passwords are hashed with **Argon2id** (`pwdlib`, the library FastAPI's docs use), minimum 12 characters and no composition rules (NIST SP 800-63B). Emails are stored lowercased, so the unique constraint is case-insensitive.
- **Server-side sessions** in a `sessions` table. Login creates a row with a 256-bit random token; the browser gets the token in a cookie and the database stores only its **SHA-256**, so a database leak cannot be replayed as cookies. Sessions last 30 days; logout deletes the row. A user's expired sessions are deleted on their next login.
- **Cookie:** `HttpOnly` (JavaScript cannot read it), `Secure` (HTTPS only; `SESSION_COOKIE_SECURE=false` only for plain-HTTP development on the LAN), `SameSite=Lax`.
- **CSRF:** `SameSite=Lax` keeps the cookie off cross-site POST/PATCH/DELETE, and a middleware rejects unsafe requests whose `Origin` header does not match the `Host`. This needs proxies to preserve `Host` (Vite's dev proxy is configured to).
- **Authorization at the router level:** every data router is mounted with the `current_user` dependency in `main.py`; only `/api/auth/*` and `/api/health` are public.
- **Login errors don't reveal accounts:** the same 401 for unknown email and wrong password, and an unknown email still runs a dummy Argon2 verification so timing does not tell them apart. Sign-up does answer 409 for a taken email; hiding that needs email confirmation, which needs an email service.

This is the same design as the Rails 8 authentication generator (`Session` model, cookie with the session id), with the token hashed at rest.

## Alternatives considered

- **JWT in the browser:** stateless, but cannot be revoked before it expires (logout, stolen device) without a denylist, which is a sessions table again. Stored in `localStorage` it is readable by any XSS.
- **Signed cookie holding the user id (Starlette `SessionMiddleware`):** no table, but also no server-side logout or "close all sessions", and it needs a secret key to manage.
- **Google login / OAuth provider:** rejected on purpose, see Context.
- **CSRF tokens:** the classic defense, but they need wiring into every form and fetch. With a same-origin SPA (Single-Page Application), `SameSite` plus the `Origin` check covers the same attacks with no client code.

## Consequences

- Every authenticated request costs one indexed query (`sessions.token_hash` is unique).
- The households PR will scope data by the user's household; until then every logged-in user sees all expenses.
- Sign-up is open. Rate limiting on login and sign-up is in the backlog and must land before deploy.
- Password reset and invitations will use one-time links shared by hand, since there is no email.
