import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import { PaymentMethodsPage } from '../../../src/pages/profile/PaymentMethodsPage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const PLAYER_ID = '00000000-0000-4000-8000-000000000003'
export const GAME_ID = '00000000-0000-4000-8000-000000000010'

export const LIST = 'GET /user-payment-methods'
export const START_SETUP = 'POST /user-payment-methods/setup-intent'
export const SAVE_CARD = 'POST /user-payment-methods/sync'
export const MAKE_DEFAULT = 'PATCH /user-payment-methods/{payment_method_id}/default'
export const REMOVE = 'DELETE /user-payment-methods/{payment_method_id}'

function endpointFor(path, method = 'GET') {
  const pathname = new URL(path, 'http://test.local').pathname
  const patterns = [
    [/^\/user-payment-methods\/(setup-intent|sync)$/, null],
    [/^\/user-payment-methods\/[^/]+\/default$/, '/user-payment-methods/{payment_method_id}/default'],
    [/^\/user-payment-methods\/[^/]+$/, '/user-payment-methods/{payment_method_id}'],
  ]
  for (const [pattern, template] of patterns) {
    if (pattern.test(pathname)) return `${method} ${template || pathname}`
  }
  return `${method} ${pathname}`
}

// Check each resolved fake answer against the response schema saved from the
// real API. Rejected requests have no answer.
afterEach(() => {
  const mockedRequest = vi.mocked(apiRequest)
  mockedRequest.mock.calls.forEach(([path, options], index) => {
    const result = mockedRequest.mock.settledResults[index]
    if (result?.type === 'fulfilled') {
      checkBackendAnswer(backendFields, endpointFor(path, options?.method || 'GET'), result.value)
    }
  })
})

export function signIn(appUser = {}) {
  vi.mocked(useAuth).mockReturnValue({
    appUser: {
      id: PLAYER_ID,
      first_name: 'Test',
      last_name: 'Player',
      date_of_birth: '1990-01-01',
      account_status: 'active',
      ...appUser,
    },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
}

let nextId = 1
// A saved card as the server returns it.
export function card(overrides = {}) {
  const suffix = String(nextId++).padStart(12, '0')
  return {
    id: `00000000-0000-4000-9000-${suffix}`,
    user_id: PLAYER_ID,
    card_brand: 'visa',
    card_last4: '4242',
    exp_month: 12,
    exp_year: 2035,
    method_status: 'active',
    is_default: false,
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    detached_at: null,
    ...overrides,
  }
}

export function setupAnswer() {
  return { client_secret: 'seti_test_123_secret_abc' }
}

// Answer each request with `answers[endpoint]`: a value, an Error to reject
// with, or a function of (path, options).
export function fakePageApi(answers = {}) {
  const allAnswers = { [LIST]: [], [START_SETUP]: setupAnswer(), ...answers }
  vi.mocked(apiRequest).mockImplementation((path, options = {}) => {
    const endpoint = endpointFor(path, options.method || 'GET')
    const answer = allAnswers[endpoint]
    if (answer === undefined) throw new Error(`No fake answer for ${endpoint}`)
    const value = typeof answer === 'function' ? answer(path, options) : answer
    if (value instanceof Error) return Promise.reject(value)
    return Promise.resolve(value)
  })
}

// The JSON bodies the page sent to an endpoint, oldest first.
export function sentBodies(endpoint) {
  return vi.mocked(apiRequest).mock.calls
    .filter(([path, options = {}]) => endpointFor(path, options.method || 'GET') === endpoint)
    .map(([, options]) => (options.body ? JSON.parse(options.body) : null))
}

export function requestCount(endpoint) {
  return sentBodies(endpoint).length
}

export function renderPaymentMethods(entry = '/profile/payment-methods') {
  const router = createMemoryRouter([
    { path: '/profile/payment-methods', element: <PaymentMethodsPage /> },
    { path: '/settings/payment-methods', element: <PaymentMethodsPage /> },
    { path: '/profile', element: <h1>Profile</h1> },
    { path: '/games/:gameId/checkout', element: <h1>Game Checkout</h1> },
  ], { initialEntries: [entry] })
  render(<RouterProvider router={router} />)
  return router
}
