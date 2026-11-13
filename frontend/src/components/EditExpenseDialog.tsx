import { useState } from 'react'
import { useDeleteExpense } from '../api/queries'
import type { ExpenseRead } from '../api/generated'
import { CloseButton, Dialog } from './Dialog'
import { ExpenseForm } from './ExpenseForm'

type Props = {
  expense: ExpenseRead
  onClose: () => void
}

export function EditExpenseDialog({ expense, onClose }: Props) {
  return (
    <Dialog
      labelledBy="edit-expense-title"
      onClose={onClose}
      className="m-auto w-full max-w-md bg-transparent p-0 backdrop:bg-black/40"
    >
      <div className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 id="edit-expense-title" className="text-lg font-semibold text-white">
              Editar gasto
            </h2>
            <p className="text-sm text-white/80">Apuntado por {expense.created_by.name}</p>
          </div>
          <CloseButton onClick={onClose} className="text-white hover:bg-white/10" />
        </div>
        <ExpenseForm expense={expense} onSaved={onClose} />
        <DeleteExpense expense={expense} onDeleted={onClose} />
      </div>
    </Dialog>
  )
}

/** Deleting is final (no trash), so it asks once more before calling the API. */
function DeleteExpense({ expense, onDeleted }: { expense: ExpenseRead; onDeleted: () => void }) {
  const deleteExpense = useDeleteExpense()
  const [confirming, setConfirming] = useState(false)

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="w-full rounded-lg bg-white py-3 font-semibold text-red-600 shadow-sm hover:bg-red-50"
      >
        Eliminar gasto
      </button>
    )
  }

  return (
    <div className="space-y-3 rounded-2xl bg-white p-4 shadow-sm">
      <p className="text-gray-700">¿Eliminar «{expense.concept}»? No se puede deshacer.</p>
      {deleteExpense.isError && (
        <p className="text-sm text-red-600">No se ha podido eliminar. Inténtalo de nuevo.</p>
      )}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => setConfirming(false)}
          className="rounded-lg border border-gray-300 py-3 font-semibold text-gray-700 hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="button"
          disabled={deleteExpense.isPending}
          onClick={() => deleteExpense.mutate(expense.id, { onSuccess: onDeleted })}
          className="rounded-lg bg-red-600 py-3 font-semibold text-white hover:bg-red-700 disabled:opacity-60"
        >
          {deleteExpense.isPending ? 'Eliminando…' : 'Sí, eliminar'}
        </button>
      </div>
    </div>
  )
}
