# 2. Store money as integer cents

Date: 2026-10-23 · Status: accepted

## Context

Expense amounts are summed, compared against bank movements and exported to spreadsheets. Binary floating point cannot represent most decimal amounts exactly (`0.1 + 0.2 != 0.3`), which shows up as off-by-one-cent totals and failed reconciliations.

## Decision

Amounts are stored and exposed by the API as **integers in cents** (`amount_cents: 1250` is 12.50 €). Conversion to and from a human-readable amount happens only at the edges: the frontend form and display, and exports.

All amounts are in euros for now; there is no currency column until there is a real need.

## Alternatives considered

- **`NUMERIC(12, 2)` + Python `Decimal`**: also exact, but JSON has no decimal type, so every client would have to parse strings or risk floats again.
- **Floats**: rejected, see context.

## Consequences

- Sums and comparisons are exact integer arithmetic, in SQL and in Python.
- API consumers (frontend, n8n, the bank-sync service) must remember the unit; the field name says it explicitly.
