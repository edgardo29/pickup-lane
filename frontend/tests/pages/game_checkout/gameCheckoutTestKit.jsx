import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { apiRequest } from '../../../src/lib/apiClient.js'
import GameCheckoutPage from '../../../src/pages/browse-games/GameCheckoutPage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const GAME_ID = '00000000-0000-4000-8000-000000000001'
export const VENUE_ID = '00000000-0000-4000-8000-000000000002'
export const PLAYER_ID = '00000000-0000-4000-8000-000000000003'
export const HOST_ID = '00000000-0000-4000-8000-000000000004'
export const BOOKING_ID = '00000000-0000-4000-8000-000000000006'
export const PAYMENT_ID = '00000000-0000-4000-8000-000000000009'
export const CARD_ID = '00000000-0000-4000-8000-000000000020'
export const OTHER_CARD_ID = '00000000-0000-4000-8000-000000000021'

function endpointFor(path, method = 'GET') {
  const pathname = new URL(path, 'http://test.local').pathname
  const patterns = [
    [/^\/checkout\/games\/[^/]+\/quote$/, '/checkout/games/{game_id}/quote'],
    [/^\/checkout\/games\/[^/]+\/payment-intent$/, '/checkout/games/{game_id}/payment-intent'],
    [/^\/checkout\/games\/[^/]+\/guest-payment-intent$/, '/checkout/games/{game_id}/guest-payment-intent'],
    [/^\/checkout\/bookings\/[^/]+\/status$/, '/checkout/bookings/{booking_id}/status'],
    [/^\/games\/[^/]+\/participants$/, '/games/{game_id}/participants'],
    [/^\/games\/[^/]+\/join$/, '/games/{game_id}/join'],
    [/^\/games\/[^/]+\/booking-guests\/add$/, '/games/{game_id}/booking-guests/add'],
    [/^\/games\/[^/]+$/, '/games/{game_id}'],
    [/^\/venues\/[^/]+$/, '/venues/{venue_id}'],
  ]
  for (const [pattern, template] of patterns) {
    if (pattern.test(pathname)) return `${method} ${template}`
  }
  return `${method} ${pathname}`
}

// Check each resolved fake answer, including answers from actions, against the
// response schema saved from the real API. Rejected requests have no answer.
afterEach(() => {
  const mockedRequest = vi.mocked(apiRequest)
  mockedRequest.mock.calls.forEach(([path, options], index) => {
    const result = mockedRequest.mock.settledResults[index]
    if (result?.type === 'fulfilled') {
      checkBackendAnswer(backendFields, endpointFor(path, options?.method || 'GET'), result.value)
    }
  })
})

export function game(overrides = {}) {
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
    ...overrides,
  }
}

export function communityGame(overrides = {}) {
  return game({
    game_type: 'community',
    payment_collection_type: 'external_host',
    price_per_player_cents: 0,
    host_user_id: HOST_ID,
    ...overrides,
  })
}

export function participant(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000007',
    game_id: GAME_ID,
    booking_id: BOOKING_ID,
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

// Other players filling spots, so a game can be made full.
export function otherPlayers(count) {
  return Array.from({ length: count }, (_, index) => participant({
    id: `00000000-0000-4000-8000-0000000001${String(index).padStart(2, '0')}`,
    user_id: `00000000-0000-4000-8000-0000000002${String(index).padStart(2, '0')}`,
    booking_id: `00000000-0000-4000-8000-0000000003${String(index).padStart(2, '0')}`,
    display_name_snapshot: `Other Player ${index + 1}`,
  }))
}

export function savedCard(overrides = {}) {
  return {
    id: CARD_ID,
    user_id: PLAYER_ID,
    card_brand: 'visa',
    card_last4: '4242',
    exp_month: 12,
    exp_year: 2035,
    method_status: 'active',
    is_default: true,
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    detached_at: null,
    ...overrides,
  }
}

export function quote(overrides = {}) {
  return {
    subtotal_cents: 1000,
    platform_fee_cents: 0,
    checkout_total_cents: 1000,
    available_credit_cents: 0,
    credit_applied_cents: 0,
    minimum_charge_adjustment_cents: 0,
    final_amount_due_cents: 1000,
    payment_required: true,
    ...overrides,
  }
}

export function paymentIntent(overrides = {}) {
  return {
    client_secret: 'pi_test_secret',
    booking_id: BOOKING_ID,
    payment_id: PAYMENT_ID,
    amount_cents: 1000,
    currency: 'USD',
    stripe_status: 'processing',
    subtotal_cents: 1000,
    platform_fee_cents: 0,
    checkout_total_cents: 1000,
    available_credit_cents: 0,
    credit_applied_cents: 0,
    minimum_charge_adjustment_cents: 0,
    final_amount_due_cents: 1000,
    stripe_amount_cents: 1000,
    payment_required: true,
    booking_status: 'pending_payment',
    booking_payment_status: 'processing',
    reservation_status: 'held',
    payment_status: 'processing',
    provider_status: 'processing',
    compensation_status: null,
    ...overrides,
  }
}

// Guest payments preserve the existing confirmed booking and its reservation.
export function guestPaymentIntent(overrides = {}) {
  return paymentIntent({ booking_status: 'confirmed', booking_payment_status: 'paid', reservation_status: 'confirmed', ...overrides })
}

export function checkoutStatus({ partySize = 1, totalSpots = 14, ...overrides } = {}) {
  const reservation = overrides.reservation_status || 'confirmed'
  const occupied = ['held', 'confirmed'].includes(reservation) ? partySize : 0
  return {
    guest_reservation_status: null,
    roster_counts: { occupied_spots: occupied, spots_remaining: Math.max(totalSpots - occupied, 0), waitlist_count: 0 },
    booking_id: BOOKING_ID,
    booking_status: 'confirmed',
    booking_payment_status: 'paid',
    reservation_status: 'confirmed',
    payment_id: PAYMENT_ID,
    payment_status: 'succeeded',
    provider_status: 'succeeded',
    compensation_status: null,
    amount_cents: 1000,
    currency: 'USD',
    subtotal_cents: 1000,
    platform_fee_cents: 0,
    checkout_total_cents: 1000,
    available_credit_cents: 0,
    credit_applied_cents: 0,
    minimum_charge_adjustment_cents: 0,
    final_amount_due_cents: 1000,
    stripe_amount_cents: 1000,
    payment_required: true,
    ...overrides,
  }
}

// Status reads retain the parent's financial totals. Only successful added
// guests increase those totals; their separate holds determine roster capacity.
export function guestCheckoutStatus({ guestCount = 1, totalSpots = 14, ...overrides } = {}) {
  const paymentStatus = overrides.payment_status || 'processing'
  const released = Boolean(overrides.compensation_status) ||
    ['requires_payment_method', 'failed', 'canceled'].includes(paymentStatus)
  const guestReservation = overrides.guest_reservation_status ||
    (released ? 'released' : paymentStatus === 'succeeded' ? 'confirmed' : 'held')
  const occupied = 1 + (guestReservation === 'released' ? 0 : guestCount)
  const total = 1000 * (1 + (guestReservation === 'confirmed' ? guestCount : 0))
  return checkoutStatus({
    guest_reservation_status: guestReservation,
    roster_counts: { occupied_spots: occupied, spots_remaining: Math.max(totalSpots - occupied, 0), waitlist_count: 0 },
    payment_status: paymentStatus, provider_status: paymentStatus,
    amount_cents: total, subtotal_cents: total, checkout_total_cents: total,
    final_amount_due_cents: total, stripe_amount_cents: total,
    ...overrides,
  })
}

export function joinAnswer(overrides = {}) {
  return {
    status: 'joined',
    message: 'You joined this game.',
    participant_id: '00000000-0000-4000-8000-000000000007',
    booking_id: BOOKING_ID,
    waitlist_entry_id: null,
    ...overrides,
  }
}

export function fakePageApi(gameAnswer, extraAnswers = {}, { rosterCounts } = {}) {
  const answers = {
    'GET /games/{game_id}': gameAnswer,
    'GET /game-images': [],
    'GET /venue-images': [],
    'GET /games/{game_id}/participants': gameAnswer?.game_type === 'community' ? [participant({ user_id: HOST_ID, booking_id: null, display_name_snapshot: 'Game Host' })] : [],
    'GET /venues/{venue_id}': new Error('Venue details unavailable'),
    'GET /user-payment-methods': [savedCard()],
    'GET /checkout/games/{game_id}/quote': (path) => {
      const params = new URL(path, 'http://test.local').searchParams
      const guests = Number(params.get('guest_count') || 0)
      const total = gameAnswer.price_per_player_cents * (params.get('add_guests') === 'true' ? guests : guests + 1)
      return quote({ subtotal_cents: total, checkout_total_cents: total, final_amount_due_cents: total })
    },
    ...extraAnswers,
  }
  // Build one consistent server snapshot before giving it to the page.
  if (!(gameAnswer instanceof Error)) {
    const participants = answers['GET /games/{game_id}/participants']
    const occupied = participants.filter((place) => ['confirmed', 'pending_payment'].includes(place.participant_status)).length
    answers['GET /games/{game_id}'] = {
      ...gameAnswer,
      roster_counts: rosterCounts || {
        occupied_spots: occupied,
        spots_remaining: Math.max(gameAnswer.total_spots - occupied, 0),
        waitlist_count: participants.filter((place) => place.participant_status === 'waitlisted').length,
      },
    }
  }
  vi.mocked(apiRequest).mockImplementation((path, options) => {
    const endpoint = endpointFor(path, options?.method || 'GET')
    const answer = answers[endpoint]
    if (answer === undefined) throw new Error(`No fake answer for ${endpoint}`)
    let value = typeof answer === 'function' ? answer(path, options) : answer
    if (endpoint === 'GET /games/{game_id}/participants' && Array.isArray(value)) {
      const params = new URL(path, 'http://test.local').searchParams
      const offset = Number(params.get('offset') || 0)
      const limit = Number(params.get('limit') || 50)
      value = value.slice(offset, offset + limit)
    }
    return value instanceof Error ? Promise.reject(value) : Promise.resolve(value)
  })
}

// The JSON body the page sent with its last request to an endpoint path.
export function sentBody(pathEnd) {
  const call = vi.mocked(apiRequest).mock.calls.findLast(([path]) => path.endsWith(pathEnd))
  return call ? JSON.parse(call[1].body) : null
}

export function renderCheckout(search = '') {
  const router = createMemoryRouter([
    { path: '/games/:gameId/checkout', element: <GameCheckoutPage /> },
    { path: '/games/:gameId', element: <h1>Game Details</h1> },
    { path: '/sign-in', element: <h1>Sign In</h1> },
    { path: '/finish-profile', element: <h1>Finish Profile</h1> },
  ], { initialEntries: [`/games/${GAME_ID}/checkout${search}`] })
  render(<RouterProvider router={router} />)
  return router
}
