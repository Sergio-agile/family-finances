import { useState } from 'react'
import type { FormEvent } from 'react'
import { useCategories, useCreateExpense } from '../api/queries'
import { todayISO } from '../lib/dates'
import { parseAmountToCents } from '../lib/money'

const inputClass =
  'h-11 w-full rounded-lg border border-gray-300 bg-white px-3 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-600/20'

export function ExpenseForm() {
  const categories = useCategories()
  const createExpense = useCreateExpense()
  const [amountError, setAmountError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)

    const amountCents = parseAmountToCents(String(data.get('amount')))
    if (amountCents === null) {
      setAmountError('Escribe un importe positivo, por ejemplo 12,50')
      return
    }
    setAmountError(null)

    createExpense.mutate(
      {
        amount_cents: amountCents,
        concept: String(data.get('concept')),
        category_id: Number(data.get('category_id')),
        spent_on: String(data.get('spent_on')),
      },
      { onSuccess: () => form.reset() },
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl bg-white p-4 shadow-sm">
      <label className="block">
        <span className="sr-only">Importe</span>
        <div className="flex items-baseline gap-2 border-b-2 border-gray-200 focus-within:border-emerald-600">
          <input
            name="amount"
            inputMode="decimal"
            placeholder="0,00"
            autoComplete="off"
            required
            aria-invalid={amountError !== null}
            className="w-full bg-transparent py-2 text-4xl font-semibold tabular-nums focus:outline-none"
          />
          <span className="text-2xl text-gray-400">€</span>
        </div>
        {amountError && <p className="mt-1 text-sm text-red-600">{amountError}</p>}
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Concepto</span>
        <input name="concept" required maxLength={200} className={inputClass} />
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="block min-w-0">
          <span className="mb-1 block text-sm font-medium text-gray-700">Categoría</span>
          <select
            name="category_id"
            required
            disabled={!categories.isSuccess}
            defaultValue=""
            className={inputClass}
          >
            <option value="" disabled>
              {categories.isPending ? 'Cargando…' : 'Elige una'}
            </option>
            {categories.data?.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>

        <label className="block min-w-0">
          <span className="mb-1 block text-sm font-medium text-gray-700">Fecha</span>
          <input
            name="spent_on"
            type="date"
            required
            defaultValue={todayISO()}
            className={inputClass}
          />
        </label>
      </div>

      {createExpense.isError && (
        <p className="text-sm text-red-600">No se ha podido guardar el gasto. Inténtalo de nuevo.</p>
      )}

      <button
        type="submit"
        disabled={createExpense.isPending}
        className="w-full rounded-lg bg-emerald-600 py-3 font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
      >
        {createExpense.isPending ? 'Guardando…' : 'Añadir gasto'}
      </button>
    </form>
  )
}
