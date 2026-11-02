# 7. An expense records who wrote it down and, optionally, whose it is

Date: 2026-11-02 · Status: accepted

## Context

Once several people share a household, the family wants to break spending down by person. "By person" can mean two different things:

- **Whose expense it is:** what was spent on each person (Ana's clothes, Sergio's gym), whoever paid.
- **Who paid:** for settling up between members.

Who *wrote it down* is a third, separate fact: useful when reviewing changes, but not a spending category.

## Decision

- **`created_by_id`** (NOT NULL): set by the API from the session on create, never accepted from the client, never editable. Shown when an expense is opened.
- **`member_id`** (optional): **whose** expense it is, chosen in the form ("De quién"); empty means the whole household's. It must be a member of the expense's household (422 otherwise). If that user is deleted, it goes back to `NULL`.
- Members are shown by **name**, never by email: `GET /api/households/{id}/members` returns `id` and `name` only.
- **Who paid** is not recorded for now. If settling up is ever needed, it becomes another optional field, independent of these two.

## Alternatives considered

- **Use `created_by` as "whose":** the person who writes an expense down is often not the person it was for.
- **A list of members per expense (shared expenses):** more flexible, but needs an extra table and a UI to pick several people. "Del hogar" already covers expenses that are everyone's.

## Consequences

- Reports can group by `member_id` (with `NULL` as "household") with a plain `GROUP BY`.
- `created_by_id` has no `ON DELETE`: a user who wrote down expenses can't be deleted while those expenses exist. Deleting accounts needs its own decision when it comes up.
- The monthly list loads members and authors with one extra query each (`selectinload`), not one per expense.
