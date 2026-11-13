import { useState } from 'react'
import type { FormEvent } from 'react'
import { useCreateIncome, useCurrentUser, useMembers } from '../api/queries'
import { todayISO } from '../lib/dates'
import { parseAmountToCents } from '../lib/money'
import { AMOUNT_ERROR, AmountField } from './AmountField'
import { OptionalSelect } from './OptionalSelect'
import { cardClass, inputClass, primaryButtonClass } from './styles'

export function IncomeForm() {
  const members = useMembers()
  const currentUser = useCurrentUser()
  const createIncome = useCreateIncome()
  const [amountError, setAmountError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)

    const amountCents = parseAmountToCents(String(data.get('amount')))
    if (amountCents === null) {
      setAmountError(AMOUNT_ERROR)
      return
    }
    setAmountError(null)

    createIncome.mutate(
      {
        amount_cents: amountCents,
        concept: String(data.get('concept')),
        // The empty option ("") means not assigned yet.
        received_by_id: Number(data.get('received_by_id')) || null,
        received_on: String(data.get('received_on')),
      },
      { onSuccess: () => form.reset() },
    )
  }

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 p-4 ${cardClass}`}>
      <AmountField error={amountError} />

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Concepto</span>
        <input
          name="concept"
          required
          maxLength={200}
          placeholder="Nómina, venta, devolución…"
          className={inputClass}
        />
      </label>

      <div className="grid grid-cols-2 gap-3">
        <label className="block min-w-0">
          <span className="mb-1 block text-sm font-medium text-gray-700">Fecha</span>
          <input
            name="received_on"
            type="date"
            required
            defaultValue={todayISO()}
            className={inputClass}
          />
        </label>
        <OptionalSelect
          name="received_by_id"
          label="Recibido por"
          emptyLabel="Sin asignar"
          options={members}
          // Usually whoever writes it down received it; it can be changed.
          defaultValue={currentUser.data?.id}
        />
      </div>

      {createIncome.isError && (
        <p className="text-sm text-red-600">No se ha podido guardar el ingreso. Inténtalo de nuevo.</p>
      )}

      <button type="submit" disabled={createIncome.isPending} className={primaryButtonClass}>
        {createIncome.isPending ? 'Guardando…' : 'Añadir ingreso'}
      </button>
    </form>
  )
}
