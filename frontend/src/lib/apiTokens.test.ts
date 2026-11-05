import { describe, expect, it } from 'vitest'
import { accessLabel } from './apiTokens'

describe('accessLabel', () => {
  it('names a read-only token', () => {
    expect(accessLabel(['expenses:read'])).toBe('Solo leer gastos')
  })

  it('names a token that writes, whatever else it has', () => {
    expect(accessLabel(['expenses:write'])).toBe('Leer y apuntar gastos')
    expect(accessLabel(['expenses:read', 'expenses:write'])).toBe('Leer y apuntar gastos')
  })
})
