import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    dir: 'tests',
    include: ['**/*.test.{js,jsx}'],
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    // Whole-page tests with simulated clicks can pass 5 seconds when every
    // test file runs at once, so they get a longer limit.
    testTimeout: 15000,
    mockReset: true,
    restoreMocks: true,
  },
})
