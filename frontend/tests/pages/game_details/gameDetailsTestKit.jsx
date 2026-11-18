import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { apiRequest } from '../../../src/lib/apiClient.js'
import GameDetailsPage from '../../../src/pages/browse-games/GameDetailsPage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const GAME_ID = '00000000-0000-4000-8000-000000000001'
export const VENUE_ID = '00000000-0000-4000-8000-000000000002'
export const PLAYER_ID = '00000000-0000-4000-8000-000000000003'
export const HOST_ID = '00000000-0000-4000-8000-000000000004'
export const CHAT_ID = '00000000-0000-4000-8000-000000000010'

function endpointFor(path, method = 'GET') {
  const pathname = new URL(path, 'http://test.local').pathname
  const patterns = [
    [/^\/games\/[^/]+\/change-removal-requests$/, '/games/{game_id}/change-removal-requests'],
    [/^\/games\/[^/]+\/change-review$/, '/games/{game_id}/change-review'],
    [/^\/games\/[^/]+\/participants$/, '/games/{game_id}/participants'],
    [/^\/games\/[^/]+\/(leave|cancel)$/, null],
    [/^\/games\/[^/]+\/guests\/(add|remove)$/, null],
    [/^\/games\/[^/]+$/, '/games/{game_id}'],
    [/^\/venues\/[^/]+$/, '/venues/{venue_id}'],
    [/^\/game-chats\/for-game\/[^/]+$/, '/game-chats/for-game/{game_id}'],
    [/^\/game-chats\/[^/]+\/(read-state|read)$/, null],
  ]
  for (const [pattern, template] of patterns) {
    const match = pathname.match(pattern)
    if (match) {
      if (template) return `${method} ${template}`
      if (pathname.includes('/guests/')) return `${method} /games/{game_id}/guests/${match[1]}`
      if (pathname.includes('/game-chats/')) return `${method} /game-chats/{game_chat_id}/${match[1]}`
      return `${method} /games/{game_id}/${match[1]}`
    }
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
    host_guest_max: 2,
    host_user_id: HOST_ID,
    roster_counts: { occupied_spots: 3, spots_remaining: 11, waitlist_count: 0 },
    ...overrides,
  }
}

export function communityGame(overrides = {}) {
  return game({
    game_type: 'community',
    payment_collection_type: 'external_host',
    price_per_player_cents: 0,
    ...overrides,
  })
}

export function participant(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000007',
    game_id: GAME_ID,
    booking_id: '00000000-0000-4000-8000-000000000006',
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

export function communityDetails(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000008',
    game_id: GAME_ID,
    payment_methods_snapshot: [],
    payment_instructions_snapshot: null,
    payment_text_moderation_status: 'visible',
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    ...overrides,
  }
}

export function gameChat(overrides = {}) {
  return {
    id: CHAT_ID,
    game_id: GAME_ID,
    chat_status: 'active',
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    closed_at: null,
    unread_count: 0,
    ...overrides,
  }
}

export function chatMessage(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000011',
    chat_id: CHAT_ID,
    sender_user_id: PLAYER_ID,
    message_type: 'text',
    message_body: 'See you there',
    is_pinned: false,
    pinned_at: null,
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    ...overrides,
  }
}

export function fakePageApi(gameAnswer, extraAnswers = {}) {
  const answers = {
    'GET /games/{game_id}': gameAnswer,
    'GET /game-images': [],
    'GET /venue-images': [],
    'GET /games/{game_id}/participants': [],
    'GET /venues/{venue_id}': new Error('Venue details unavailable'),
    'GET /community-game-details': [],
    'GET /games/{game_id}/change-review': {
      changes: [], active_request: null, can_request_removal: false,
    },
    ...extraAnswers,
  }
  vi.mocked(apiRequest).mockImplementation((path, options) => {
    const endpoint = endpointFor(path, options?.method || 'GET')
    const answer = answers[endpoint]
    if (answer instanceof Error) return Promise.reject(answer)
    if (typeof answer === 'function') return Promise.resolve(answer(path, options))
    if (answer === undefined) throw new Error(`No fake answer for ${endpoint}`)
    return Promise.resolve(answer)
  })
}

export function renderGame() {
  const router = createMemoryRouter([
    { path: '/games/:gameId', element: <GameDetailsPage /> },
    { path: '/games/browse', element: <h1>Browse Games</h1> },
    { path: '/games/:gameId/checkout', element: <h1>Game Checkout</h1> },
    { path: '/create-account', element: <h1>Create Account</h1> },
    { path: '/finish-profile', element: <h1>Finish Profile</h1> },
    { path: '/sign-in', element: <h1>Sign In</h1> },
  ], { initialEntries: [`/games/${GAME_ID}`] })
  render(<RouterProvider router={router} />)
  return router
}
