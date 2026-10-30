import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // In development, forward /api calls to FastAPI so the browser sees a single origin (no CORS).
    // Keep the browser's Host header (the string shorthand would rewrite it to localhost:8000):
    // the API's CSRF check compares it with the Origin header.
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: false },
    },
  },
})
