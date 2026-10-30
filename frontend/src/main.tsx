import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { client } from './api/generated/client.gen'
import { currentUserKey } from './api/queries'

const queryClient = new QueryClient()

// A 401 from any endpoint means the session is gone (expired, or logged out in another tab):
// forgetting the user makes the app show the login screen.
client.interceptors.response.use((response) => {
  if (response.status === 401) queryClient.setQueryData(currentUserKey, null)
  return response
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
