import { useState } from 'react'
import { useExpenses } from '../api/queries'
import type { ExpenseRead } from '../api/generated'
import { formatDay } from '../lib/dates'
import { formatCents } from '../lib/money'
import { EditExpenseDialog } from './EditExpenseDialog'
import { listCardClass, rowButtonClass } from './styles'

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

  return (
    <section className="space-y-4">
      <h2 className="text-sm font-medium uppercase tracking-wide text-gray-500">Gastos</h2>

      {expenses.data.length === 0 && (
        <p className="py-8 text-center text-gray-500">Todavía no hay gastos este mes.</p>
      )}

      {groupByDay(expenses.data).map(([day, dayExpenses]) => (
        <div key={day}>
          <h3 className="mb-1 text-sm font-medium text-gray-500 first-letter:uppercase">{formatDay(day)}</h3>
          <ul className={listCardClass}>
            {dayExpenses.map((expense) => (
              <li key={expense.id}>
                <button
                  type="button"
                  onClick={() => setEditing(expense)}
                  className={rowButtonClass}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{expense.concept}</p>
                    <p className="text-sm text-gray-500">
                      {expense.category.name} ·{' '}
                      {expense.spending_type?.name ?? (
                        <span className="text-amber-600">Sin clasificar</span>
                      )}
                      {' · '}
                      {expense.paid_by?.name ?? (
                        <span className="text-amber-600">Sin pagador</span>
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
