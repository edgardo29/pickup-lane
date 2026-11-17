import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    dir: 'tests',
    include: ['**/*.test.{js,jsx}'],
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    mockReset: true,
    restoreMocks: true,
  },
})
