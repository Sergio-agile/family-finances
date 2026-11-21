import { describe, expect, it } from 'vitest'
import type { IncomeRead } from '../api/generated'
import { groupIncomesByReceiver } from './incomes'

const ana = { id: 1, name: 'Ana' }
const bea = { id: 2, name: 'Bea' }

function income(id: number, amount_cents: number, received_by: IncomeRead['received_by']) {
  return {
    id,
    amount_cents,
    received_by,
    concept: 'Consultas',
    received_on: '2026-11-03',
    created_by: ana,
    created_at: '2026-11-03T10:00:00Z',
  } as IncomeRead
}

describe('groupIncomesByReceiver', () => {
  it('returns no groups for no incomes', () => {
    expect(groupIncomesByReceiver([])).toEqual([])
  })

  it('totals each member, sorted by name, with the unassigned group last', () => {
    const groups = groupIncomesByReceiver([
      income(1, 5000, null),
      income(2, 12000, bea),
      income(3, 3000, ana),
      income(4, 8000, bea),
    ])

    expect(groups.map((group) => [group.receiver?.name ?? null, group.totalCents])).toEqual([
      ['Ana', 3000],
      ['Bea', 20000],
      [null, 5000],
    ])
  })

  it("keeps each group's incomes in the order they came", () => {
    const [group] = groupIncomesByReceiver([income(7, 100, ana), income(3, 200, ana)])

    expect(group.incomes.map((item) => item.id)).toEqual([7, 3])
  })
})
