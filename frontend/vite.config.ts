import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development, forward /api calls to FastAPI so the browser sees a single origin (no CORS).
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
