import type { ApiTokenRead } from '../api/generated'

type Scope = ApiTokenRead['scopes'][number]

/** The two kinds of access a token can have, as the user chooses them. Writing implies reading
 * (the API grants `expenses:read` to `expenses:write` tokens). */
export const ACCESS_OPTIONS: { scope: Scope; label: string; hint: string }[] = [
  { scope: 'expenses:read', label: 'Solo leer gastos', hint: 'Para informes y resúmenes.' },
  {
    scope: 'expenses:write',
    label: 'Leer y apuntar gastos',
    hint: 'Para importar movimientos del banco.',
  },
]

/** What a token can do, in the same words the user picked it with. */
export function accessLabel(scopes: Scope[]): string {
  const scope = scopes.includes('expenses:write') ? 'expenses:write' : 'expenses:read'
  return ACCESS_OPTIONS.find((option) => option.scope === scope)!.label
}
