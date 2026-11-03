# 12. Personal access tokens with scopes, denied by default

Date: 2026-11-03 · Status: accepted

## Context

Scripts and integrations (n8n: bank import, weekly summaries) need to call the API. They can't log in with a password and a cookie, and they shouldn't hold a person's password anyway. Each integration should be able to do only what it needs, and be cut off on its own if it leaks.

## Decision

- **Personal access tokens**, like GitHub's: created by a logged-in user, sent as `Authorization: Bearer ff_…`, acting as that user. Household access works exactly as with a session (ADR 0005): another household is a 404.
- **Random 256-bit token with an `ff_` prefix**, so a leaked one is recognizable by secret scanners (gitleaks, GitHub). **Only its SHA-256 is stored**, as with sessions (ADR 0004); it is shown once, on creation.
- **Scopes**: `expenses:read` (expenses, categories, spending types, members) and `expenses:write` (create and edit expenses), which **implies read**, since an importer needs the categories to write.
- **FastAPI's own mechanism**: endpoints declare what they need with `Security(current_user, scopes=[…])`, and `current_user` checks it through `SecurityScopes`. The session-or-token lookup is a separate dependency without scopes, so it runs once per request.
- **Denied by default**: a token only passes where an endpoint declares scopes. Everything else (managing tokens, invitations, `/me`, and any endpoint added later without scopes) answers 403 to tokens. A leaked token can't create more tokens or invite anyone.
- **Revoking** deletes the token: it stops working on the next request. Missing scope → 403 with `WWW-Authenticate: Bearer error="insufficient_scope"` (RFC 6750); unknown token → 401.
- **`last_used_at`**, updated at most once a minute, so a bulk import doesn't write on every request.
- At most 20 tokens per user, which also bounds the list.

## Alternatives considered

- **A full OAuth 2 server** (authorization code, client registration, refresh tokens): the right tool when third-party apps act on behalf of users. Here the user creates the token for their own scripts; the scopes give the same least-privilege idea with a fraction of the moving parts.
- **Tokens bound to a household** instead of to the user: a bit less reach for each token, but one more concept for a family that has a single household. Can be added as an optional field.
- **Mandatory expiry** (GitHub's fine-grained tokens): limits the damage of an unnoticed leak, but an n8n flow that silently stops after 90 days is its own failure. Revocation plus `last_used_at` covers it for now; expiry can be added as an option.
- **JWTs**: no database lookup, but they can't be revoked before they expire without keeping a deny list, which brings the lookup back.

## Consequences

- Swagger lists both security schemes (cookie and bearer) on every protected endpoint, because both go through the same dependency; session-only endpoints still answer 403 to tokens.
- A token can do anything its user can within its scopes, including in every household the user belongs to.
- Every new endpoint is session-only until it declares a scope, which is the safe default.
