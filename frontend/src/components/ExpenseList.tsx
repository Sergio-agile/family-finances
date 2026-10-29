import { useState } from 'react'
import { useExpenses } from '../api/queries'
import type { ExpenseRead } from '../api/generated'
import { formatDay } from '../lib/dates'
import { formatCents } from '../lib/money'
import { EditExpenseDialog } from './EditExpenseDialog'

/** Groups expenses by day, keeping the API's newest-first order. */
function groupByDay(expenses: ExpenseRead[]): [string, ExpenseRead[]][] {
  const groups = new Map<string, ExpenseRead[]>()
  for (const expense of expenses) {
    groups.set(expense.spent_on, [...(groups.get(expense.spent_on) ?? []), expense])
  }
  return [...groups]
}

export function ExpenseList({ month }: { month: string }) {
  const expenses = useExpenses(month)
  const [editing, setEditing] = useState<ExpenseRead | null>(null)

  if (expenses.isPending) return <p className="text-center text-gray-500">Cargando gastos…</p>
  if (expenses.isError)
    return <p className="text-center text-red-600">No se han podido cargar los gastos.</p>

  // Derived from server data on every render instead of being stored as separate state.
  const total = expenses.data.reduce((sum, expense) => sum + expense.amount_cents, 0)

  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-medium uppercase tracking-wide text-gray-500">Total del mes</h2>
        <p className="text-2xl font-semibold tabular-nums">{formatCents(total)}</p>
      </div>

      {expenses.data.length === 0 && (
        <p className="py-8 text-center text-gray-500">Todavía no hay gastos este mes.</p>
      )}

      {groupByDay(expenses.data).map(([day, dayExpenses]) => (
        <div key={day}>
          <h3 className="mb-1 text-sm font-medium text-gray-500 first-letter:uppercase">{formatDay(day)}</h3>
          <ul className="divide-y divide-gray-100 overflow-hidden rounded-2xl bg-white shadow-sm">
            {dayExpenses.map((expense) => (
              <li key={expense.id}>
                <button
                  type="button"
                  onClick={() => setEditing(expense)}
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{expense.concept}</p>
                    <p className="text-sm text-gray-500">
                      {expense.category.name} ·{' '}
                      {expense.spending_type?.name ?? (
                        <span className="text-amber-600">Sin clasificar</span>
                      )}
                    </p>
                  </div>
                  <p className="shrink-0 font-semibold tabular-nums">
                    {formatCents(expense.amount_cents)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {editing && <EditExpenseDialog expense={editing} onClose={() => setEditing(null)} />}
    </section>
  )
}
