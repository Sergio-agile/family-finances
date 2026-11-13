import { useIncomes } from '../api/queries'
import { formatDay } from '../lib/dates'
import { formatCents } from '../lib/money'
import { listCardClass } from './styles'

export function IncomeList({ month }: { month: string }) {
  const incomes = useIncomes(month)

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
        <ul className={listCardClass}>
          {incomes.data.map((income) => (
            <li key={income.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{income.concept}</p>
                <p className="text-sm text-gray-500 first-letter:uppercase">
                  {formatDay(income.received_on)} ·{' '}
                  {income.received_by?.name ?? <span className="text-amber-600">Sin asignar</span>}
                </p>
              </div>
              <p className="shrink-0 font-semibold tabular-nums text-emerald-700">
                +{formatCents(income.amount_cents)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
