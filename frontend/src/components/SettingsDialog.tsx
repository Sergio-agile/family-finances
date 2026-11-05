import type { ReactNode } from 'react'
import { useLogOut, useMembers } from '../api/queries'
import type { UserRead } from '../api/generated'
import { ApiTokensSection } from './ApiTokensSection'
import { CloseButton, Dialog } from './Dialog'
import { InviteSection } from './InviteSection'

type Props = {
  user: UserRead
  onClose: () => void
}

/**
 * Everything that is not daily use: account, household and integrations. Full screen on phones,
 * centered on larger screens. A dialog, not a page, until the app has a router (see backlog).
 */
export function SettingsDialog({ user, onClose }: Props) {
  const logOut = useLogOut()
  const household = user.households[0]

  return (
    <Dialog
      labelledBy="settings-title"
      onClose={onClose}
      className="m-0 h-full max-h-none w-full max-w-none bg-gray-50 p-0 text-gray-900 backdrop:bg-black/40 sm:m-auto sm:h-auto sm:max-h-[90vh] sm:max-w-md sm:rounded-2xl"
    >
      <div className="mx-auto max-w-md space-y-6 px-4 py-6">
        <header className="flex items-center justify-between">
          <h2 id="settings-title" className="text-2xl font-bold">
            Ajustes
          </h2>
          <CloseButton onClick={onClose} className="text-gray-500 hover:bg-gray-200" />
        </header>

        <Section title="Tu cuenta">
          <div className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow-sm">
            <div className="min-w-0 text-sm">
              <p className="truncate font-medium">{user.name}</p>
              <p className="truncate text-gray-500">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={() => logOut.mutate()}
              disabled={logOut.isPending}
              className="shrink-0 text-sm font-semibold text-emerald-700 disabled:opacity-60"
            >
              Salir
            </button>
          </div>
        </Section>

        <Section title={`Hogar «${household.name}»`}>
          <Members />
          <InviteSection householdName={household.name} />
        </Section>

        <Section title="Avanzado">
          <ApiTokensSection />
        </Section>
      </div>
    </Dialog>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500">{title}</h3>
      {children}
    </section>
  )
}

/** The household's members. Usually already cached: the expense form uses them for "paid by". */
function Members() {
  const members = useMembers()

  if (members.isPending) return <p className="text-sm text-gray-500">Cargando miembros…</p>
  if (members.isError)
    return <p className="text-sm text-red-600">No se han podido cargar los miembros.</p>

  return (
    <ul className="divide-y divide-gray-100 rounded-2xl bg-white px-4 shadow-sm">
      {members.data.map((member) => (
        <li key={member.id} className="py-3 text-sm">
          {member.name}
        </li>
      ))}
    </ul>
  )
}
