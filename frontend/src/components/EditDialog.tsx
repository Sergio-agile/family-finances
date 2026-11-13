import { useState } from 'react'
import type { ReactNode } from 'react'
import { CloseButton, Dialog } from './Dialog'
import { cardClass } from './styles'

type Props = {
  /** "gasto" or "ingreso": the dialog says "Editar gasto", "Eliminar gasto"… */
  noun: string
  concept: string
  createdBy: string
  onClose: () => void
  onDelete: () => void
  /** The state of the delete mutation. */
  deletion: { isPending: boolean; isError: boolean }
  /** The edit form. */
  children: ReactNode
}

/** The dialog that opens when an expense or an income is tapped: its form, and a way to delete it. */
export function EditDialog({
  noun,
  concept,
  createdBy,
  onClose,
  onDelete,
  deletion,
  children,
}: Props) {
  return (
    <Dialog
      labelledBy="edit-dialog-title"
      onClose={onClose}
      className="m-auto w-full max-w-md bg-transparent p-0 backdrop:bg-black/40"
    >
      <div className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 id="edit-dialog-title" className="text-lg font-semibold text-white">
              Editar {noun}
            </h2>
            <p className="text-sm text-white/80">Apuntado por {createdBy}</p>
          </div>
          <CloseButton onClick={onClose} className="text-white hover:bg-white/10" />
        </div>
        {children}
        <ConfirmDelete noun={noun} concept={concept} onDelete={onDelete} deletion={deletion} />
      </div>
    </Dialog>
  )
}

/** Deleting is final (no trash), so it asks once more before calling the API. */
function ConfirmDelete({
  noun,
  concept,
  onDelete,
  deletion,
}: Pick<Props, 'noun' | 'concept' | 'onDelete' | 'deletion'>) {
  const [confirming, setConfirming] = useState(false)

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="w-full rounded-lg bg-white py-3 font-semibold text-red-600 shadow-sm hover:bg-red-50"
      >
        Eliminar {noun}
      </button>
    )
  }

  return (
    <div className={`space-y-3 p-4 ${cardClass}`}>
      <p className="text-gray-700">¿Eliminar «{concept}»? No se puede deshacer.</p>
      {deletion.isError && (
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
          disabled={deletion.isPending}
          onClick={onDelete}
          className="rounded-lg bg-red-600 py-3 font-semibold text-white hover:bg-red-700 disabled:opacity-60"
        >
          {deletion.isPending ? 'Eliminando…' : 'Sí, eliminar'}
        </button>
      </div>
    </div>
  )
}
