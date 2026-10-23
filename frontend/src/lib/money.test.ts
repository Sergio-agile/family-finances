import { describe, expect, it } from 'vitest'
import { formatCents, parseAmountToCents } from './money'

describe('parseAmountToCents', () => {
  it.each([
    ['12', 1200],
    ['12,5', 1250],
    ['12,50', 1250],
    ['12.50', 1250],
    ['0.29', 29],
    [' 3,99 ', 399],
  ])('parses %j as %i cents', (input, cents) => {
    expect(parseAmountToCents(input)).toBe(cents)
  })

  it.each(['', 'abc', '12,345', '1.234,56', '-5', '0', '0,00', '12,'])(
    'rejects %j',
    (input) => {
      expect(parseAmountToCents(input)).toBeNull()
    },
  )
})

describe('formatCents', () => {
  it('formats cents as euros in Spanish style', () => {
    // Intl uses a non-breaking space before the € sign.
    expect(formatCents(123456).replace(/\s/g, ' ')).toBe('1234,56 €')
  })
})
