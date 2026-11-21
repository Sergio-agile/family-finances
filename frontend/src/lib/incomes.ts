import type { IncomeRead } from '../api/generated'

export type IncomeGroup = {
  /** The member who received the incomes, or null for the ones nobody is assigned to. */
  receiver: IncomeRead['received_by']
  totalCents: number
  incomes: IncomeRead[]
}

/**
 * A month's incomes grouped by who received them, each group with its total.
 * Members are sorted by name, with the unassigned group last; each group keeps the API's order.
 */
export function groupIncomesByReceiver(incomes: IncomeRead[]): IncomeGroup[] {
  const groups = new Map<number | null, IncomeGroup>()
  for (const income of incomes) {
    const key = income.received_by?.id ?? null
    let group = groups.get(key)
    if (!group) {
      group = { receiver: income.received_by, totalCents: 0, incomes: [] }
      groups.set(key, group)
    }
    group.totalCents += income.amount_cents
    group.incomes.push(income)
  }

  return [...groups.values()].sort((a, b) => {
    if (!a.receiver) return 1
    if (!b.receiver) return -1
    return a.receiver.name.localeCompare(b.receiver.name, 'es')
  })
}
