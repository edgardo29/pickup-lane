import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import GameCheckoutPage from '../../../src/pages/browse-games/GameCheckoutPage.jsx'
import { PaymentMethodsPage } from '../../../src/pages/profile/PaymentMethodsPage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const PLAYER_ID = '00000000-0000-4000-8000-000000000003'
export const GAME_ID = '00000000-0000-4000-8000-000000000010'
export const VENUE_ID = '00000000-0000-4000-8000-000000000011'

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
    [/^\/checkout\/games\/[^/]+\/quote$/, '/checkout/games/{game_id}/quote'],
    [/^\/games\/[^/]+\/participants$/, '/games/{game_id}/participants'],
    [/^\/games\/[^/]+$/, '/games/{game_id}'],
    [/^\/venues\/[^/]+$/, '/venues/{venue_id}'],
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

// An official game with in-app payment, as Game Checkout loads it.
export function checkoutGame() {
  return {
    id: GAME_ID,
    game_type: 'official',
    payment_collection_type: 'in_app',
    publish_status: 'published',
    game_status: 'active',
    public_visibility_status: 'visible',
    join_enforcement_status: 'open',
    title: 'Evening Pickup',
    description: null,
    venue_id: VENUE_ID,
    venue_name_snapshot: 'Central Field',
    address_snapshot: '100 Main St',
    city_snapshot: 'Chicago',
    state_snapshot: 'IL',
    neighborhood_snapshot: null,
    starts_at: '2030-06-15T23:00:00Z',
    ends_at: '2030-06-16T00:00:00Z',
    starts_on_local: '2030-06-15',
    timezone: 'America/Chicago',
    format_label: '7v7',
    game_player_group: 'coed',
    skill_level: 'all',
    environment_type: 'outdoor',
    total_spots: 14,
    price_per_player_cents: 1000,
    currency: 'USD',
    allow_guests: true,
    max_guests_per_booking: 2,
    waitlist_enabled: true,
    is_chat_enabled: true,
    custom_rules_text: null,
    custom_cancellation_text: null,
    game_notes: null,
    parking_notes: null,
    cancelled_at: null,
    cancel_reason: null,
    host_guest_max: 0,
    host_user_id: null,
    roster_counts: { occupied_spots: 0, spots_remaining: 14, waitlist_count: 0 },
  }
}

export function checkoutVenue() {
  return {
    id: VENUE_ID,
    name: 'Central Field',
    address_line_1: '100 Main St',
    city: 'Chicago',
    state: 'IL',
    postal_code: '60601',
    country_code: 'US',
    neighborhood: null,
    latitude: null,
    longitude: null,
    external_place_id: null,
    venue_status: 'approved',
    created_by_user_id: null,
    approved_by_user_id: null,
    approved_at: null,
    is_active: true,
    created_at: '2029-01-01T18:00:00Z',
    updated_at: '2029-01-01T18:00:00Z',
    deleted_at: null,
  }
}

// The player's own roster place, with guests booked on it as needed.
export function myRosterPlace(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000012',
    game_id: GAME_ID,
    booking_id: '00000000-0000-4000-8000-000000000013',
    participant_type: 'registered_user',
    user_id: PLAYER_ID,
    guest_of_user_id: null,
    display_name_snapshot: 'Test Player',
    participant_status: 'confirmed',
    cancellation_type: 'none',
    roster_order: 1,
    joined_at: '2029-06-15T18:00:00Z',
    confirmed_at: '2029-06-15T18:00:00Z',
    cancelled_at: null,
    ...overrides,
  }
}

// The price for the player and guests, or for added guests only.
export function checkoutQuote({ guestCount = 0, addGuests = false } = {}) {
  const cents = 1000 * (addGuests ? guestCount : guestCount + 1)
  return {
    subtotal_cents: cents,
    platform_fee_cents: 0,
    checkout_total_cents: cents,
    available_credit_cents: 0,
    credit_applied_cents: 0,
    minimum_charge_adjustment_cents: 0,
    final_amount_due_cents: cents,
    payment_required: true,
  }
}

// The answers Game Checkout needs to load for an official game. The server
// counts confirmed and held roster places as taken spots.
export function checkoutAnswers({ participants = [] } = {}) {
  const game = checkoutGame()
  const takenSpots = participants.filter(
    (place) => ['confirmed', 'pending_payment'].includes(place.participant_status),
  ).length
  return {
    'GET /games/{game_id}': {
      ...game,
      roster_counts: {
        occupied_spots: takenSpots,
        spots_remaining: game.total_spots - takenSpots,
        waitlist_count: 0,
      },
    },
    'GET /games/{game_id}/participants': participants,
    'GET /game-images': [],
    'GET /venue-images': [],
    'GET /venues/{venue_id}': checkoutVenue(),
    'GET /checkout/games/{game_id}/quote': (path) => {
      const params = new URL(path, 'http://test.local').searchParams
      return checkoutQuote({
        guestCount: Number(params.get('guest_count') || 0),
        addGuests: params.get('add_guests') === 'true',
      })
    },
  }
}

// Start on Game Checkout, which links to Payment Methods.
export function renderFromCheckout(search = '') {
  const router = createMemoryRouter([
    { path: '/games/:gameId/checkout', element: <GameCheckoutPage /> },
    { path: '/games/:gameId', element: <h1>Game Details</h1> },
    { path: '/profile/payment-methods', element: <PaymentMethodsPage /> },
    { path: '/profile', element: <h1>Profile</h1> },
  ], { initialEntries: [`/games/${GAME_ID}/checkout${search}`] })
  render(<RouterProvider router={router} />)
  return router
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
