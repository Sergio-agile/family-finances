import { useState } from 'react'
import type { FormEvent } from 'react'
import { useCreateIncome, useCurrentUser, useMembers, useUpdateIncome } from '../api/queries'
import type { IncomeCreate, IncomeRead } from '../api/generated'
import { todayISO } from '../lib/dates'
import { centsToInput, parseAmountToCents } from '../lib/money'
import { AMOUNT_ERROR, AmountField } from './AmountField'
import { OptionalSelect } from './OptionalSelect'
import { cardClass, inputClass, primaryButtonClass } from './styles'

type Props = {
  /** When given, the form edits this income instead of creating a new one. */
  income?: IncomeRead
  onSaved?: () => void
}

export function IncomeForm({ income, onSaved }: Props) {
  const members = useMembers()
  const currentUser = useCurrentUser()
  const createIncome = useCreateIncome()
  const updateIncome = useUpdateIncome()
  const mutation = income ? updateIncome : createIncome
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

    const values: IncomeCreate = {
      amount_cents: amountCents,
      concept: String(data.get('concept')),
      // The empty option ("") means not assigned yet.
      received_by_id: Number(data.get('received_by_id')) || null,
      received_on: String(data.get('received_on')),
    }

    if (income) {
      updateIncome.mutate({ id: income.id, changes: values }, { onSuccess: onSaved })
    } else {
      createIncome.mutate(values, {
        onSuccess: () => {
          form.reset()
          onSaved?.()
        },
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 p-4 ${cardClass}`}>
      <AmountField
        defaultValue={income && centsToInput(income.amount_cents)}
        error={amountError}
      />

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-gray-700">Concepto</span>
        <input
          name="concept"
          required
          maxLength={200}
          placeholder="Nómina, venta, devolución…"
          defaultValue={income?.concept}
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
            defaultValue={income?.received_on ?? todayISO()}
            className={inputClass}
          />
        </label>
        <OptionalSelect
          name="received_by_id"
          label="Recibido por"
          emptyLabel="Sin asignar"
          options={members}
          // Usually whoever writes it down received it; it can be changed.
          defaultValue={income ? income.received_by?.id : currentUser.data?.id}
        />
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600">No se ha podido guardar el ingreso. Inténtalo de nuevo.</p>
      )}

      <button type="submit" disabled={mutation.isPending} className={primaryButtonClass}>
        {mutation.isPending ? 'Guardando…' : income ? 'Guardar cambios' : 'Añadir ingreso'}
      </button>
    </form>
  )
}
