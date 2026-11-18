import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

// Tests never reach a real server. Pages get data from a faked API module;
// any other network request fails loudly.
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    throw new Error(`Unexpected network request in a frontend test: ${url}`)
  }))
})

// Remove anything a test rendered so the next test starts from a blank page.
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})
