# 7. An expense records who wrote it down and who paid it

Date: 2026-11-02 · Status: accepted

## Context

Once several people share a household, the family wants to break spending down by person. The app will also track each member's income, to compare what each person earns with what they spend. For that, what matters is **whose money paid** an expense, not who it was for: if Sergio pays for someone's dance classes, it comes out of Sergio's income.

Who *wrote it down* is a separate fact: useful when reviewing changes, but not part of any report.

## Decision

- **`created_by_id`** (NOT NULL): set by the API from the session on create, never accepted from the client, never editable. Shown when an expense is opened ("Apuntado por …").
- **`paid_by_id`** (optional): the member who paid, chosen in the form ("Pagado por"). The form preselects the logged-in user, since whoever writes an expense down usually paid it; it can be changed then or later (someone else handed over the cash). It must be a member of the expense's household (422 otherwise). If that user is deleted, it goes back to `NULL`.
- The API does not default the payer: an expense without one (from a bank import, n8n…) is **not assigned yet**, like an expense without a spending type. The list flags it in amber ("Sin pagador") so it gets filled in later.
- Members are shown by **name**, never by email: `GET /api/households/{id}/members` returns `id` and `name` only.
- **Who it was for** is not recorded. If it is ever needed, it becomes another optional field.

## Alternatives considered

- **Use `created_by` as the payer:** the person who writes an expense down is often not the one who paid.
- **Required payer:** forces a choice at the till, when the family may not know or care yet. It also doesn't fit bank imports, where the payer is filled in later.
- **Split payments (several payers per expense):** needs an extra table with amounts per person. A shared expense can be entered as two expenses for now.

## Consequences

- Reports can group by `paid_by_id` per member, and per household, with `NULL` as "unassigned", using a plain `GROUP BY`. Later, the same grouping can be compared against each member's income.
- `created_by_id` has no `ON DELETE`: a user who wrote down expenses can't be deleted while those expenses exist. Deleting accounts needs its own decision when it comes up.
- The monthly list loads payers and authors with one extra query each (`selectinload`), not one per expense.
