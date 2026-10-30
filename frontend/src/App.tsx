import { useState } from 'react'
import { useCurrentUser, useLogOut } from './api/queries'
import { AuthScreen } from './components/AuthScreen'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'
import { currentMonth } from './lib/dates'

export default function App() {
  const currentUser = useCurrentUser()

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {currentUser.isPending ? null : currentUser.isError ? (
        <p className="py-12 text-center text-red-600">No se ha podido conectar con el servidor.</p>
      ) : currentUser.data ? (
        <Home email={currentUser.data.email} />
      ) : (
        <AuthScreen />
      )}
    </div>
  )
}

function Home({ email }: { email: string }) {
  const [month, setMonth] = useState(currentMonth)
  const logOut = useLogOut()

  return (
    <main className="mx-auto max-w-md space-y-6 px-4 py-6">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Family Finances</h1>
        <label>
          <span className="sr-only">Mes</span>
          <input
            type="month"
            value={month}
            onChange={(event) => event.target.value && setMonth(event.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-2 py-1 text-sm"
          />
        </label>
      </header>

      <ExpenseForm />
      <ExpenseList month={month} />

      <footer className="flex items-center justify-between gap-3 text-sm text-gray-500">
        <span className="truncate">{email}</span>
        <button
          type="button"
          onClick={() => logOut.mutate()}
          disabled={logOut.isPending}
          className="shrink-0 font-semibold text-emerald-700 disabled:opacity-60"
        >
          Salir
        </button>
      </footer>
    </main>
  )
}
