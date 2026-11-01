# 5. Households scope the data, through nested routes

Date: 2026-10-30 · Status: accepted

## Context

Expenses belong to a family, not to one person: everyone in the house adds and edits the same list. The app may later open to other families, and nobody may ever see another family's data. A person can also belong to more than one household (for example, their own and their parents').

## Decision

- A **`households`** table and a **`memberships`** table (user × household, unique together). Sign-up creates a household called "Mi hogar" and makes the new user its member. Roles (owner/member) are left out until something needs them.
- Every expense has a **`household_id`** (NOT NULL, `ON DELETE CASCADE`).
- Expense routes are **nested under the household**: `/api/households/{household_id}/expenses`. One dependency, `CurrentHousehold`, loads the household only if the logged-in user is a member, and every expense query filters by it.
- Someone else's household or expense answers **404, not 403**, so ids of other families cannot be probed.
- One composite index, `(household_id, spent_on)`, serves the monthly list. It replaces the old index on `spent_on` alone, which every query now bypasses.
- Categories and spending types stay **global** for now: they are the same default lists for everyone.
- The frontend works on the user's first household. A household switcher can come later without API changes.

## Alternatives considered

- **Current household stored in the session** (`/api/expenses`, household implied): shorter URLs, but hidden state. Two tabs on two households would interfere, and API tokens (n8n) would need their own way to choose. With the household in the URL, every request says what it touches, the same way for the browser and for tokens.
- **Postgres Row-Level Security:** the database enforces the filter even if the code forgets it. It is stronger, but needs a per-request `SET` of the user, a non-owner database role and careful testing. That's a lot of moving parts for a few tables; a single dependency plus isolation tests is enough at this size. It can be added later as a second layer.
- **A `user_id` on each expense instead of households:** sharing a list would then need sharing rules between users. A household is the thing being shared.

## Consequences

- Every expense request costs one extra indexed query (the membership check).
- A new data router must take `CurrentHousehold` and filter by it. The isolation tests in `test_expenses.py` are the pattern to copy.
- The migration moves existing development data (users and expenses) into one shared "Mi hogar". Production starts empty.
- Invitations to join an existing household come next. Until then, each sign-up gets its own household.
