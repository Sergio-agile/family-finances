import { describe, expect, it } from 'vitest'
import { readInvitation } from './invitation'

describe('readInvitation', () => {
  it('reads the token after the #', () => {
    expect(readInvitation('#invitation=abc-123_XYZ')).toBe('abc-123_XYZ')
  })

  it('returns null without an invitation', () => {
    expect(readInvitation('')).toBeNull()
    expect(readInvitation('#something=else')).toBeNull()
  })
})
