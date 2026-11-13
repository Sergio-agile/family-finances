import { useExpenses, useIncomes } from '../api/queries'
import { formatCents, sumCents } from '../lib/money'
import { cardClass } from './styles'

/**
 * What came in, what went out and what is left this month. It reads the same cached queries as
 * the lists below, so it adds no requests of its own.
 */
export function MonthSummary({ month }: { month: string }) {
  const incomes = useIncomes(month)
  const expenses = useExpenses(month)

  // The lists show loading and errors; the summary only appears once both totals are known.
  if (!incomes.isSuccess || !expenses.isSuccess) return null

  const income = sumCents(incomes.data)
  const spent = sumCents(expenses.data)
  const balance = income - spent

  return (
    <section
      aria-label="Resumen del mes"
      className={`grid grid-cols-3 gap-2 p-4 text-center ${cardClass}`}
    >
      <Figure label="Ingresos" cents={income} className="text-emerald-700" />
      <Figure label="Gastos" cents={spent} />
      <Figure
        label="Diferencia"
        cents={balance}
        className={balance < 0 ? 'text-red-600' : 'text-emerald-700'}
      />
    </section>
  )
}

type FigureProps = { label: string; cents: number; className?: string }

function Figure({ label, cents, className = '' }: FigureProps) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`truncate font-semibold tabular-nums sm:text-lg ${className}`}>
        {formatCents(cents)}
      </p>
    </div>
  )
}
