import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  useCategories,
  useCreateExpense,
  useCurrentUser,
  useMembers,
  useSpendingTypes,
  useUpdateExpense,
} from '../api/queries'
import type { ExpenseCreate, ExpenseRead } from '../api/generated'
import { todayISO } from '../lib/dates'
import { centsToInput, parseAmountToCents } from '../lib/money'
import { OptionalSelect } from './OptionalSelect'
import { inputClass, primaryButtonClass } from './styles'

type Props = {
  /** When given, the form edits this expense instead of creating a new one. */
  expense?: ExpenseRead
  onSaved?: () => void
}

export function ExpenseForm({ expense, onSaved }: Props) {
  const categories = useCategories()
  const spendingTypes = useSpendingTypes()
  const members = useMembers()
  const currentUser = useCurrentUser()
  const createExpense = useCreateExpense()
  const updateExpense = useUpdateExpense()
  const mutation = expense ? updateExpense : createExpense
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
    // The empty option of an optional select ("") is sent as null.
    const optionalId = (field: string) => Number(data.get(field)) || null

    const values: ExpenseCreate = {
      amount_cents: amountCents,
      concept: String(data.get('concept')),
      category_id: Number(data.get('category_id')),
      spending_type_id: optionalId('spending_type_id'),
      paid_by_id: optionalId('paid_by_id'),
      spent_on: String(data.get('spent_on')),
    }

    if (expense) {
      updateExpense.mutate({ id: expense.id, changes: values }, { onSuccess: onSaved })
    } else {
      createExpense.mutate(values, {
        onSuccess: () => {
          form.reset()
          onSaved?.()
        },
      })
    }
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
            defaultValue={expense && centsToInput(expense.amount_cents)}
            aria-invalid={amountError !== null}
            className="w-full bg-transparent py-2 text-4xl font-semibold tabular-nums focus:outline-none"
          />
          <span className="text-2xl text-gray-400">€</span>
        </div>
        {amountError && <p className="mt-1 text-sm text-red-600">{amountError}</p>}
      </label>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Concepto</span>
        <input
          name="concept"
          required
          maxLength={200}
          defaultValue={expense?.concept}
          className={inputClass}
        />
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="block min-w-0">
          <span className="mb-1 block text-sm font-medium text-gray-700">Categoría</span>
          <select
            name="category_id"
            required
            disabled={!categories.isSuccess}
            defaultValue={expense?.category.id ?? ''}
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
            defaultValue={expense?.spent_on ?? todayISO()}
            className={inputClass}
          />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <OptionalSelect
          name="spending_type_id"
          label="Tipo"
          emptyLabel="Sin clasificar"
          options={spendingTypes}
          defaultValue={expense?.spending_type?.id}
        />
        <OptionalSelect
          name="paid_by_id"
          label="Pagado por"
          emptyLabel="Sin asignar"
          options={members}
          // A new expense is usually paid by whoever writes it down; it can be changed.
          defaultValue={expense ? expense.paid_by?.id : currentUser.data?.id}
        />
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600">No se ha podido guardar el gasto. Inténtalo de nuevo.</p>
      )}

      <button
        type="submit"
        disabled={mutation.isPending}
        className={primaryButtonClass}
      >
        {mutation.isPending ? 'Guardando…' : expense ? 'Guardar cambios' : 'Añadir gasto'}
      </button>
    </form>
  )
}
