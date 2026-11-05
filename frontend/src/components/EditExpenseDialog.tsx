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
      </div>
    </Dialog>
  )
}
