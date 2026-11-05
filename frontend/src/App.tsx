import { useState } from 'react'
import { useCurrentUser } from './api/queries'
import type { UserRead } from './api/generated'
import { AuthScreen } from './components/AuthScreen'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'
import { SettingsDialog } from './components/SettingsDialog'
import { currentMonth } from './lib/dates'
import { readInvitation } from './lib/invitation'

export default function App() {
  const currentUser = useCurrentUser()

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {currentUser.isPending ? null : currentUser.isError ? (
        <p className="py-12 text-center text-red-600">No se ha podido conectar con el servidor.</p>
      ) : currentUser.data ? (
        <Home user={currentUser.data} />
      ) : (
        <AuthScreen />
      )}
    </div>
  )
}

function Home({ user }: { user: UserRead }) {
  const [month, setMonth] = useState(currentMonth)
  // An invitation link opened while logged in can't be used: say so instead of ignoring it.
  const [hasInvitation] = useState(() => readInvitation() !== null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <main className="mx-auto max-w-md space-y-6 px-4 py-6">
      <header className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold">Family Finances</h1>
          <p className="truncate text-sm text-gray-500">{user.households[0].name}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <label>
            <span className="sr-only">Mes</span>
            <input
              type="month"
              value={month}
              onChange={(event) => event.target.value && setMonth(event.target.value)}
              className="rounded-lg border border-gray-300 bg-white px-2 py-1 text-sm"
            />
          </label>
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            aria-label="Ajustes"
            className="rounded-full p-2 text-gray-500 hover:bg-gray-200"
          >
            <GearIcon />
          </button>
        </div>
      </header>

      {hasInvitation && (
        <p className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">
          Has abierto un enlace de invitación, pero ya has entrado como{' '}
          <strong className="break-all">{user.email}</strong>. Para crear otra cuenta con él, entra en
          Ajustes (el engranaje de arriba) y pulsa «Salir».
        </p>
      )}

      <ExpenseForm />
      <ExpenseList month={month} />
      {settingsOpen && <SettingsDialog user={user} onClose={() => setSettingsOpen(false)} />}
    </main>
  )
}

/** Inline, so the app needs no icon library for one icon. */
function GearIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="size-5">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10.3 4.3c.4-1.7 3-1.7 3.4 0a1.7 1.7 0 0 0 2.6 1.1c1.5-.9 3.3.8 2.4 2.4a1.7 1.7 0 0 0 1 2.5c1.8.5 1.8 3 0 3.5a1.7 1.7 0 0 0-1 2.5c.9 1.6-.9 3.3-2.4 2.4a1.7 1.7 0 0 0-2.6 1.1c-.4 1.7-3 1.7-3.4 0a1.7 1.7 0 0 0-2.6-1.1c-1.5.9-3.3-.8-2.4-2.4a1.7 1.7 0 0 0-1-2.5c-1.8-.5-1.8-3 0-3.5a1.7 1.7 0 0 0 1-2.5c-.9-1.6.9-3.3 2.4-2.4a1.7 1.7 0 0 0 2.6-1.1Z"
      />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}
