import { useDeleteIncome } from '../api/queries'
import type { IncomeRead } from '../api/generated'
import { EditDialog } from './EditDialog'
import { IncomeForm } from './IncomeForm'

type Props = {
  income: IncomeRead
  onClose: () => void
}

export function EditIncomeDialog({ income, onClose }: Props) {
  const deleteIncome = useDeleteIncome()

  return (
    <EditDialog
      noun="ingreso"
      concept={income.concept}
      createdBy={income.created_by.name}
      onClose={onClose}
      onDelete={() => deleteIncome.mutate(income.id, { onSuccess: onClose })}
      deletion={deleteIncome}
    >
      <IncomeForm income={income} onSaved={onClose} />
    </EditDialog>
  )
}
