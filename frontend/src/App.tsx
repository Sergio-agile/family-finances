import { useState } from 'react'
import { ExpenseForm } from './components/ExpenseForm'
import { ExpenseList } from './components/ExpenseList'
import { currentMonth } from './lib/dates'

export default function App() {
  const [month, setMonth] = useState(currentMonth)

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
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
      </main>
    </div>
  )
}
