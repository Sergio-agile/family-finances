# 6. Invite-only sign-up with one-time links

Date: 2026-11-01 · Status: accepted. Changes the sign-up part of [ADR 0005](0005-households-scope-the-data.md).

## Context

With open sign-up, anyone with the URL could create an account (and a household) on a public deployment. For now the app is for one family. Other families may come later, but that's a separate decision. There is still no email service.

## Decision

- **Sign-up requires an invitation.** An invitation is a one-time link to join a specific household; the new account becomes a member of that household. Sign-up no longer creates households.
- **Any member can invite** from the app ("Invitar a alguien a …"). Roles can restrict this later.
- Invitations live in an **`invitations`** table, like sessions: a 256-bit random token in the link, only its SHA-256 stored, **7-day expiry**. Expired invitations of a household are deleted when it creates a new one.
- **One use, guaranteed by the database:** sign-up consumes the invitation with a single `DELETE … RETURNING`, so two simultaneous sign-ups cannot both use it. If sign-up fails (taken email), nothing is committed and the link still works.
- The token goes **after `#`** (`https://app/#invitation=…`). Browsers never send the fragment to the server, so the token doesn't end up in access logs or `Referer` headers.
- **The first household** comes from the command line, which prints its sign-up link: `uv run python -m app.invitations "Casa García"`. This needs server access, the same as running migrations.
- The link is built from the URL the browser used (`request.base_url`), so a link made from the phone on the LAN (Local Area Network) points to the LAN address. The command line uses the `APP_URL` setting.

## Alternatives considered

- **An env flag `SIGNUP_ENABLED`:** closes sign-up, but then nobody else can join either.
- **Invitations by email:** need an email service and its deliverability. A link shared by WhatsApp reaches a family faster.
- **Mark invitations as used instead of deleting them:** keeps a history (who joined with which link). Nothing needs that yet.

## Consequences

- Opening sign-up to other families later is a small change: when a sign-up comes without a token, create a new household for it (the code ADR 0005 had).
- A logged-in user who opens an invitation link isn't offered to join that second household yet. Joining another household with an existing account comes with the household switcher.
- Invitations can't be listed or revoked yet; they expire in 7 days.
