# 9. Production refuses unsafe settings; the API sets its own security headers

Date: 2026-11-02 · Status: accepted

## Context

The app is about to go to production on a self-managed server, with real financial data. Development needs relaxed settings (plain HTTP from the phone, Swagger, any host). The risk is shipping those to production by mistake, and relying on the reverse proxy to remember every security header.

## Decision

- An **`ENVIRONMENT`** setting (`development` by default, or `production`). In production the settings **refuse to load** (so the app won't start) unless the session cookie is `Secure`, `APP_URL` uses `https://` and `ALLOWED_HOSTS` lists real domains. A misconfiguration shows up at deploy time, not as a vulnerability. Errors never print the settings' values (`hide_input_in_errors`), so the database password can't leak into logs.
- **No Swagger, ReDoc or `/openapi.json` in production.** The frontend client is generated from `app.openapi()` in development, which doesn't depend on those routes.
- **`TrustedHostMiddleware`** with `ALLOWED_HOSTS`. The Origin check (ADR 0004) and invitation links (ADR 0006) trust the `Host` header, so requests for any other host are rejected with 400.
- **Security headers on every API response**, set by the app itself so they don't depend on proxy configuration:
  - `Cache-Control: no-store`: financial data is never kept by the browser's disk cache or a proxy.
  - `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`: a JSON response can never be run or framed as a page.
  - `Referrer-Policy: no-referrer`.
  - `Strict-Transport-Security` (2 years), only in production, so development over plain HTTP keeps working.
- The headers of the frontend's HTML (its own CSP, HSTS) belong where it is served, decided in the deploy.

## Alternatives considered

- **All headers at the reverse proxy only:** a single place for both API and frontend, but nothing tests it, and a proxy change could silently drop them. The API's headers are covered by tests.
- **Swagger in production behind login:** handy for debugging, but it's a map of the API for an attacker who gets a session, and nobody in the family needs it.

## Consequences

- Production needs `ENVIRONMENT=production`, `APP_URL`, `ALLOWED_HOSTS` and `DATABASE_URL` set, and `SESSION_COOKIE_SECURE` left at true.
- HSTS is hard to undo: once a browser has seen it, that domain only works over HTTPS for two years. That's the point, but the domain must have HTTPS working before the first production response.
