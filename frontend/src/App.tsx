import { useQuery } from '@tanstack/react-query'

type Health = { status: string; database: string }

async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/health')
  if (!response.ok) throw new Error(`API responded ${response.status}`)
  return response.json()
}

export default function App() {
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth })

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 px-4">
      <h1 className="text-3xl font-bold">Family Finances</h1>
      <p className="text-gray-600">
        {health.isPending && 'Connecting to the API…'}
        {health.isError && `API unavailable: ${health.error.message}`}
        {health.isSuccess && `API ${health.data.status} · database ${health.data.database}`}
      </p>
    </main>
  )
}
