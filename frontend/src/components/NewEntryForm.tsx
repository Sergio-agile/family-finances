import { useState } from 'react'
import { ExpenseForm } from './ExpenseForm'
import { IncomeForm } from './IncomeForm'

const KINDS = [
  { value: 'expense', label: 'Gasto' },
  { value: 'income', label: 'Ingreso' },
] as const

type Kind = (typeof KINDS)[number]['value']

/** The form at the top of the home screen: a switch between writing down an expense or an income. */
export function NewEntryForm() {
  const [kind, setKind] = useState<Kind>('expense')

  return (
    <div className="space-y-3">
      <div
        role="group"
        aria-label="¿Qué quieres apuntar?"
        className="grid grid-cols-2 rounded-xl bg-gray-200 p-1"
      >
        {KINDS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            aria-pressed={kind === value}
            onClick={() => setKind(value)}
            className="rounded-lg py-2 font-medium text-gray-600 aria-pressed:bg-white aria-pressed:text-gray-900 aria-pressed:shadow-sm"
          >
            {label}
          </button>
        ))}
      </div>
      {kind === 'expense' ? <ExpenseForm /> : <IncomeForm />}
    </div>
  )
}
