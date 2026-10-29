import type { ExpenseRead } from '../api/generated'
import { ExpenseForm } from './ExpenseForm'

type Props = {
  expense: ExpenseRead
  onClose: () => void
}

/** Native <dialog> as a modal: focus trap, Escape to close and backdrop come from the browser. */
export function EditExpenseDialog({ expense, onClose }: Props) {
  return (
    <dialog
      // Opens as soon as it is mounted, so the parent only decides whether to render it.
      ref={(dialog) => {
        if (dialog && !dialog.open) dialog.showModal()
      }}
      onClose={onClose}
      // A click on the dialog element itself (not its content) is a click on the backdrop.
      onClick={(event) => event.target === event.currentTarget && onClose()}
      aria-labelledby="edit-expense-title"
      className="m-auto w-full max-w-md bg-transparent p-0 backdrop:bg-black/40"
    >
      <div className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <h2 id="edit-expense-title" className="text-lg font-semibold text-white">
            Editar gasto
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-full px-3 py-1 text-2xl leading-none text-white hover:bg-white/10"
          >
            ×
          </button>
        </div>
        <ExpenseForm expense={expense} onSaved={onClose} />
      </div>
    </dialog>
  )
}
