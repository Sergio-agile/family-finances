# 3. Spending type is a separate, per-expense dimension

Date: 2026-10-29 · Status: accepted

## Context

Categories say *what* the money went on (Supermercado, Ocio, Ropa…). The family also wants to know *what kind* of spending it was, to see how much goes to essentials versus luxuries or small recurring purchases. The five spending types are: Gastos básicos, Educación, Lujos, Gasto hormiga and Ahorro/Inversión.

The same category can fall into different types: a dinner out can be a luxury (an anniversary) or "gasto hormiga" (the everyday coffee). The type is also a judgement that may be made later, when reviewing the month, not only when the expense is entered.

## Decision

- Each expense has its own **optional** `spending_type_id`, independent of its category. It can be set on create; editing it later comes with `PATCH /api/expenses/{id}`.
- Spending types live in a **`spending_types` table**, seeded like categories, and are exposed through `GET /api/spending-types`. The API lists them in seed order (essential to optional), not alphabetically.
- An expense without a type is "not classified yet".

## Alternatives considered

- **Type fixed per category** (Supermercado is always basic): simpler, but loses exactly the nuance above. A *suggested* default type per category can still be added later on top of this decision.
- **Python/Postgres enum instead of a table**: no join, but renaming or adding a type needs a migration and the Spanish labels would have to live in code. A table keeps it consistent with categories.
- **Required field**: would force a choice before the family has thought about it, and existing expenses have no type.

## Consequences

- Reports can cross both dimensions (category × type), and can show how much is still unclassified.
- The "Educación" category and the "Educación" type overlap on purpose; they will usually go together, but nothing enforces it.
