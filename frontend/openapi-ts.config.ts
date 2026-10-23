import { defineConfig } from '@hey-api/openapi-ts'

// Generates a typed client from the backend's OpenAPI schema. Run `npm run gen:api`.
export default defineConfig({
  input: './openapi.json',
  output: 'src/api/generated',
  plugins: ['@hey-api/client-fetch'],
})
