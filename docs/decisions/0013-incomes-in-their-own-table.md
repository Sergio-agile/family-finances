# 13. Incomes live in their own table

Date: 2026-11-13 · Status: accepted

## Context

The family wants to write down what comes in (salaries, sales, refunds…) next to what goes out, to see each month's balance and, later, a monthly report. ADR 0007 already planned to compare each member's income with what they paid.

An income shares a few fields with an expense (amount, concept, date, household, who wrote it down), but not the rest: it has no category or spending type, and instead of a payer it has the member who **received** it.

## Decision

- A separate **`incomes`** table: `amount_cents`, `concept`, `received_on`, optional `received_by_id` (a member of the household; `NULL` = not assigned yet, as for `paid_by_id`), `created_by_id`, `household_id`. Index on `(household_id, received_on)`, like expenses.
- **No income categories for now:** the concept ("Nómina octubre") is enough. If the monthly report needs them, they come as an optional column.
- Endpoints under `/api/households/{id}/incomes`, mirroring expenses: `GET ?month=YYYY-MM` and `POST` first; editing and deleting in the next PR.
- **Browser sessions only** for now: API tokens get `incomes:read` / `incomes:write` scopes in their own PR, when an integration needs them (tokens are denied by default, ADR 0012).
- What expenses and incomes share is code, not schema: the `month` parameter, its date bounds and the "is this person a member?" check live in `app/routers/common.py`.

## Alternatives considered

- **One `transactions` table with a `kind` (expense/income):** the monthly report would be one `GROUP BY kind` instead of two sums, but every expense-only column would be `NULL` for incomes, validations would depend on `kind`, and it means renaming `expenses` everywhere (API, tokens' scopes, frontend) in an app already in production.
- **Negative amounts in `expenses`:** the cheapest change, and the most confusing: categories and spending types make no sense for income, and every sum would need to split by sign.

## Consequences

- The monthly report adds up each table with its own `SUM … GROUP BY`, in SQL; per member, `paid_by_id` against `received_by_id`.
- A bank import (n8n) routes each movement by sign to one endpoint or the other.
- Two lists to keep consistent in the UI: the home screen shows incomes in their own block above the expenses.
