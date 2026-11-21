import { useState } from 'react'
import { useIncomes } from '../api/queries'
import type { IncomeRead } from '../api/generated'
import { formatDay } from '../lib/dates'
import { groupIncomesByReceiver } from '../lib/incomes'
import { formatCents, sumCents } from '../lib/money'
import { EditIncomeDialog } from './EditIncomeDialog'
import { listCardClass, rowButtonClass } from './styles'

/**
 * A month's incomes as one total per member, so they don't push the expenses down the page.
 * Each member folds open (native <details>, no state) to show and edit their incomes.
 */
export function IncomeList({ month }: { month: string }) {
  const incomes = useIncomes(month)
  const [editing, setEditing] = useState<IncomeRead | null>(null)

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-medium uppercase tracking-wide text-gray-500">Ingresos</h2>
      {incomes.isPending ? (
        <p className="text-center text-gray-500">Cargando ingresos…</p>
      ) : incomes.isError ? (
        <p className="text-center text-red-600">No se han podido cargar los ingresos.</p>
      ) : incomes.data.length === 0 ? (
        <p className="py-4 text-center text-gray-500">Todavía no hay ingresos este mes.</p>
      ) : (
        <div className={listCardClass}>
          {groupIncomesByReceiver(incomes.data).map((group) => (
            <details key={group.receiver?.id ?? 'unassigned'} className="group">
              <summary
                className={`${rowButtonClass} cursor-pointer list-none [&::-webkit-details-marker]:hidden`}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <ChevronIcon />
                  <span className="truncate font-medium">
                    {group.receiver?.name ?? <span className="text-amber-600">Sin asignar</span>}
                  </span>
                  <span className="shrink-0 text-sm text-gray-500">({group.incomes.length})</span>
                </span>
                <span className="shrink-0 font-semibold tabular-nums text-emerald-700">
                  +{formatCents(group.totalCents)}
                </span>
              </summary>
              <ul className="divide-y divide-gray-100 border-t border-gray-100">
                {group.incomes.map((income) => (
                  <li key={income.id}>
                    <button
                      type="button"
                      onClick={() => setEditing(income)}
                      className={rowButtonClass}
                    >
                      <div className="min-w-0">
                        <p className="truncate">{income.concept}</p>
                        <p className="text-sm text-gray-500 first-letter:uppercase">
                          {formatDay(income.received_on)}
                        </p>
                      </div>
                      <p className="shrink-0 tabular-nums text-emerald-700">
                        +{formatCents(income.amount_cents)}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            </details>
          ))}
          <p className="flex justify-between gap-3 px-4 py-3 font-semibold">
            <span>Total</span>
            <span className="tabular-nums text-emerald-700">
              +{formatCents(sumCents(incomes.data))}
            </span>
          </p>
        </div>
      )}
      {editing && <EditIncomeDialog income={editing} onClose={() => setEditing(null)} />}
    </section>
  )
}

/** Points right when folded and down when open. Inline, so the app needs no icon library. */
function ChevronIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      className="size-4 shrink-0 text-gray-400 transition-transform group-open:rotate-90"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m9 6 6 6-6 6" />
    </svg>
  )
}
