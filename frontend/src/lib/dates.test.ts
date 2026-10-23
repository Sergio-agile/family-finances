import { describe, expect, it } from 'vitest'
import { currentMonth, formatDay, todayISO } from './dates'

describe('todayISO', () => {
  it('uses the local date, even just after midnight', () => {
    expect(todayISO(new Date(2026, 9, 23, 0, 30))).toBe('2026-10-23')
  })

  it('pads month and day', () => {
    expect(todayISO(new Date(2026, 0, 5))).toBe('2026-01-05')
  })
})

describe('currentMonth', () => {
  it('returns YYYY-MM', () => {
    expect(currentMonth(new Date(2026, 11, 31))).toBe('2026-12')
  })
})

describe('formatDay', () => {
  it('formats a date in Spanish', () => {
    expect(formatDay('2026-10-23')).toBe('viernes, 23 de octubre')
  })
})
