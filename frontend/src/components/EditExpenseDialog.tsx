import { useDeleteExpense } from '../api/queries'
import type { ExpenseRead } from '../api/generated'
import { EditDialog } from './EditDialog'
import { ExpenseForm } from './ExpenseForm'

type Props = {
  expense: ExpenseRead
  onClose: () => void
}

export function EditExpenseDialog({ expense, onClose }: Props) {
  const deleteExpense = useDeleteExpense()

  return (
    <EditDialog
      noun="gasto"
      concept={expense.concept}
      createdBy={expense.created_by.name}
      onClose={onClose}
      onDelete={() => deleteExpense.mutate(expense.id, { onSuccess: onClose })}
      deletion={deleteExpense}
    >
      <ExpenseForm expense={expense} onSaved={onClose} />
    </EditDialog>
  )
}
