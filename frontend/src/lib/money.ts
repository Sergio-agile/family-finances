const AMOUNT_PATTERN = /^(\d+)(?:[.,](\d{1,2}))?$/

/**
 * Parse what the user typed ("12", "12,5", "12.50") into integer cents.
 * Returns null for anything that isn't a positive amount with at most two decimals.
 * Works on the string digits, never on floats, so "0.29" is exactly 29.
 */
export function parseAmountToCents(input: string): number | null {
  const match = AMOUNT_PATTERN.exec(input.trim())
  if (!match) return null

  const [, euros, decimals = ''] = match
  const cents = Number(euros) * 100 + Number(decimals.padEnd(2, '0'))
  return cents > 0 ? cents : null
}

const euroFormatter = new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' })

export function formatCents(cents: number): string {
  return euroFormatter.format(cents / 100)
}
