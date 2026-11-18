import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import CreateGamePage from '../../../src/pages/create-game/CreateGamePage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const GAME_ID = '00000000-0000-4000-8000-000000000001'
export const VENUE_ID = '00000000-0000-4000-8000-000000000002'
export const HOST_ID = '00000000-0000-4000-8000-000000000003'

export const SAVE_GAME = 'PATCH /games/{game_id}/host-edit'
export const SAVE_DETAILS = 'PUT /community-game-details/games/{game_id}/host-edit'

// Sign in as the game's host; pass fields to change the account.
export function signIn(appUser = {}) {
  vi.mocked(useAuth).mockReturnValue({
    appUser: {
      id: HOST_ID, first_name: 'Test', last_name: 'Host', date_of_birth: '1990-01-01',
      account_status: 'active', email_verified_at: '2029-06-15T18:00:00Z', ...appUser,
    },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
    refreshCurrentUserVerification: vi.fn(),
    sendCurrentUserVerificationEmail: vi.fn(),
  })
}

// Step from the loaded Game step to Review without changing anything.
export async function goToReview(user) {
  await user.click(await screen.findByRole('button', { name: /^Next: Location/ }))
  await user.click(screen.getByRole('button', { name: /^Next: Notes/ }))
  await user.click(screen.getByRole('button', { name: /^Next: Review/ }))
}

function endpointFor(path, method = 'GET') {
  const pathname = new URL(path, 'http://test.local').pathname
  const patterns = [
    [/^\/community-game-details\/games\/[^/]+\/host-edit$/, '/community-game-details/games/{game_id}/host-edit'],
    [/^\/games\/[^/]+\/host-edit$/, '/games/{game_id}/host-edit'],
    [/^\/games\/[^/]+$/, '/games/{game_id}'],
    [/^\/venues\/[^/]+$/, '/venues/{venue_id}'],
  ]
  for (const [pattern, template] of patterns) {
    if (pattern.test(pathname)) return `${method} ${template}`
  }
  return `${method} ${pathname}`
}

// Check each resolved fake answer, including answers from saves, against the
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

// Three days from now at 6 PM local time, inside the 21-day scheduling limit.
function upcomingStartDate(hour) {
  const start = new Date()
  start.setDate(start.getDate() + 3)
  start.setHours(hour, 0, 0, 0)
  return start
}

function upcomingStart(hour) {
  return upcomingStartDate(hour).toISOString()
}

function upcomingLocalDate() {
  const start = upcomingStartDate(18)
  return [
    start.getFullYear(),
    String(start.getMonth() + 1).padStart(2, '0'),
    String(start.getDate()).padStart(2, '0'),
  ].join('-')
}

export function game(overrides = {}) {
  return {
    id: GAME_ID,
    game_type: 'community',
    payment_collection_type: 'external_host',
    publish_status: 'published',
    game_status: 'active',
    public_visibility_status: 'visible',
    join_enforcement_status: 'open',
    title: 'Central Field 7v7',
    description: null,
    venue_id: VENUE_ID,
    venue_name_snapshot: 'Central Field',
    address_snapshot: '100 Main St, Chicago, IL 60601',
    city_snapshot: 'Chicago',
    state_snapshot: 'IL',
    neighborhood_snapshot: 'Loop',
    starts_at: upcomingStart(18),
    ends_at: upcomingStart(19),
    starts_on_local: upcomingLocalDate(),
    timezone: 'America/Chicago',
    format_label: '7v7',
    game_player_group: 'coed',
    skill_level: 'intermediate',
    environment_type: 'outdoor',
    total_spots: 14,
    price_per_player_cents: 500,
    currency: 'USD',
    allow_guests: true,
    max_guests_per_booking: 2,
    waitlist_enabled: true,
    is_chat_enabled: true,
    custom_rules_text: 'No slide tackles.',
    custom_cancellation_text: null,
    game_notes: 'Bring water.',
    parking_notes: null,
    cancelled_at: null,
    cancel_reason: null,
    host_guest_max: 2,
    host_user_id: HOST_ID,
    roster_counts: { occupied_spots: 1, spots_remaining: 13, waitlist_count: 0 },
    ...overrides,
  }
}

export function venue(overrides = {}) {
  return {
    id: VENUE_ID,
    name: 'Central Field',
    address_line_1: '100 Main St',
    city: 'Chicago',
    state: 'IL',
    postal_code: '60601',
    country_code: 'US',
    neighborhood: 'Loop',
    latitude: null,
    longitude: null,
    external_place_id: null,
    venue_status: 'approved',
    created_by_user_id: HOST_ID,
    approved_by_user_id: HOST_ID,
    approved_at: '2029-06-15T18:00:00Z',
    is_active: true,
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    deleted_at: null,
    ...overrides,
  }
}

export function communityDetails(overrides = {}) {
  return {
    id: '00000000-0000-4000-8000-000000000008',
    game_id: GAME_ID,
    payment_methods_snapshot: [{ type: 'venmo', value: '@host' }],
    payment_instructions_snapshot: null,
    payment_text_moderation_status: 'visible',
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    ...overrides,
  }
}

export function fakePageApi(gameAnswer, extraAnswers = {}) {
  const answers = {
    'GET /games/{game_id}': gameAnswer,
    'GET /venues/{venue_id}': venue(),
    'GET /community-game-details/games/{game_id}/host-edit': communityDetails(),
    'PATCH /games/{game_id}/host-edit': gameAnswer,
    'PUT /community-game-details/games/{game_id}/host-edit': communityDetails(),
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

// How many requests the page sent to an endpoint, e.g. 'PATCH /games/{game_id}/host-edit'.
export function requestCount(endpoint) {
  return vi.mocked(apiRequest).mock.calls.filter(
    ([path, options]) => endpointFor(path, options?.method || 'GET') === endpoint,
  ).length
}

// The JSON body the page sent with its last request to an endpoint.
export function sentBody(endpoint) {
  const call = vi.mocked(apiRequest).mock.calls.findLast(
    ([path, options]) => endpointFor(path, options?.method || 'GET') === endpoint,
  )
  return call ? JSON.parse(call[1].body) : null
}

export function renderEditGame() {
  const router = createMemoryRouter([
    { path: '/games/:gameId/edit', element: <CreateGamePage /> },
    { path: '/games/:gameId', element: <h1>Game Details</h1> },
  ], { initialEntries: [`/games/${GAME_ID}/edit`] })
  render(<RouterProvider router={router} />)
  return router
}
