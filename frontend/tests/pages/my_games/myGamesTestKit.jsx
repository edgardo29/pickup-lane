import { act, render } from '@testing-library/react'
import { useSyncExternalStore } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import { MyGamesPage } from '../../../src/pages/my-games/index.js'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const PLAYER_ID = '00000000-0000-4000-8000-000000000003'
export const OTHER_PLAYER_ID = '00000000-0000-4000-8000-000000000004'

export const GAMES = 'GET /my-games'
export const NEED_A_SUB = 'GET /my-games/need-a-sub'

function endpointFor(path, method = 'GET') {
  const pathname = new URL(path, 'http://test.local').pathname
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

// The signed-in account, kept outside React like the real auth provider, so
// changing it re-renders the page the way switching accounts does in the app.
let authState = null
const authListeners = new Set()

function subscribeToAuth(listener) {
  authListeners.add(listener)
  return () => authListeners.delete(listener)
}

// Sign in a player; pass fields to change the account. Calling it again while
// the page is shown switches accounts.
export function signIn(appUser = {}) {
  const id = appUser.id || PLAYER_ID
  authState = {
    appUser: {
      id, first_name: 'Test', last_name: 'Player', date_of_birth: '1990-01-01',
      account_status: 'active', email_verified_at: '2029-06-15T18:00:00Z', ...appUser,
    },
    currentUser: { getIdToken: vi.fn().mockResolvedValue(`token-${id}`) },
    isLoading: false,
  }
  vi.mocked(useAuth).mockImplementation(
    () => useSyncExternalStore(subscribeToAuth, () => authState),
  )
  act(() => authListeners.forEach((listener) => listener()))
}

let nextId = 1
function uuid() {
  const suffix = String(nextId++).padStart(12, '0')
  return `00000000-0000-4000-8000-${suffix}`
}

// A time's calendar date ("2030-06-15") and hour ("18") where the game or
// post happens, as the server works them out.
function localDate(iso, timeZone) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date(iso))
}

function localHour(iso, timeZone) {
  return new Intl.DateTimeFormat('en-GB', { timeZone, hour: '2-digit', hourCycle: 'h23' }).format(new Date(iso))
}

// The label the server gives a game card.
function gameStatus(gameStatusValue, bucket, isHost) {
  if (gameStatusValue === 'cancelled') return ['Cancelled', 'cancelled']
  if (bucket === 'history') return isHost ? ['Hosted', 'hosted'] : ['Completed', 'completed']
  return isHost ? ['Hosting', 'hosting'] : ['Confirmed', 'confirmed']
}

// A game card as the server builds it. `startsAt` is an ISO time.
export function gameItem({
  startsAt = '2030-06-15T23:00:00Z',
  venue = 'Central Field',
  bucket = 'upcoming',
  isHost = false,
  ...overrides
} = {}) {
  const endsAt = new Date(new Date(startsAt).getTime() + 60 * 60 * 1000).toISOString()
  const id = overrides.id || uuid()
  const gameType = overrides.game?.game_type || 'official'
  const timeZone = overrides.game?.timezone || 'America/Chicago'
  // A cancelled game's players are cancelled too, so none of them hold a spot.
  const participantCount = overrides.game?.game_status === 'cancelled' ? 0 : 6
  const game = {
    id,
    game_type: gameType,
    game_status: 'active',
    public_visibility_status: 'visible',
    join_enforcement_status: 'open',
    title: `${venue} 7v7`,
    // An official game is shown by its venue; a community game by its title.
    display_title: gameType === 'official' ? venue : `${venue} 7v7`,
    venue_name_snapshot: venue,
    city_snapshot: 'Chicago',
    state_snapshot: 'IL',
    location_label: 'Chicago, IL',
    starts_at: startsAt,
    ends_at: endsAt,
    starts_on_local: localDate(startsAt, timeZone),
    registration_closes_at: new Date(new Date(startsAt).getTime() + 5 * 60 * 1000).toISOString(),
    time_group_key: `${localHour(startsAt, timeZone)}:00`,
    timezone: timeZone,
    format_label: '7v7',
    game_player_group: 'coed',
    environment_type: 'outdoor',
    total_spots: 14,
    participant_count: participantCount,
    price_per_player_cents: 1000,
    price_label: '$10',
    currency: 'USD',
    primary_image_url: null,
    availability: {
      status: 'open', total_spots: 14, occupied_spots: participantCount, spots_remaining: 14 - participantCount,
    },
    ...overrides.game,
  }
  // Publishing a community game gives its host a confirmed roster place; an
  // official game's host has none.
  const hasRosterPlace = !isHost || game.game_type === 'community'
  const [statusLabel, statusTone] = gameStatus(game.game_status, bucket, isHost)
  return {
    bucket,
    game,
    is_host: isHost,
    participant_id: hasRosterPlace ? uuid() : null,
    participant_status: hasRosterPlace ? 'confirmed' : null,
    cancellation_type: hasRosterPlace ? 'none' : null,
    status_label: statusLabel,
    status_tone: statusTone,
    ...overrides.card,
  }
}

// The label the server gives a Need a Sub card.
function postStatus(postStatusValue, bucket, isOwner) {
  if (postStatusValue === 'cancelled') return ['Cancelled', 'cancelled']
  if (isOwner) return ['Your Post', 'owner']
  return bucket === 'history' ? ['Ended', 'ended'] : ['Confirmed', 'confirmed']
}

// A Need a Sub card as the server builds it.
export function postItem({
  startsAt = '2030-06-15T23:00:00Z',
  location = 'Union Park',
  bucket = 'upcoming',
  canViewDetail = true,
  isOwner = true,
  ...overrides
} = {}) {
  const endsAt = new Date(new Date(startsAt).getTime() + 60 * 60 * 1000).toISOString()
  const id = overrides.id || uuid()
  // A cancelled post's requests are cancelled too, so no sub stays confirmed.
  const confirmedCount = overrides.post?.post_status === 'cancelled' ? 0 : 1
  const post = {
    id,
    post_status: 'active',
    public_visibility_status: 'visible',
    sport_type: 'soccer',
    location_name: location,
    neighborhood: null,
    city: 'Chicago',
    state: 'IL',
    starts_at: startsAt,
    ends_at: endsAt,
    expires_at: startsAt,
    timezone: 'America/Chicago',
    format_label: '7v7',
    game_player_group: 'coed',
    skill_level: 'intermediate',
    environment_type: 'outdoor',
    subs_needed: 2,
    confirmed_count: confirmedCount,
    pending_count: 0,
    sub_waitlist_count: 0,
    price_due_at_venue_cents: 0,
    currency: 'USD',
    positions: [{
      id: uuid(),
      sub_post_id: id,
      position_label: 'field_player',
      player_group: 'open',
      spots_needed: 2,
      confirmed_count: confirmedCount,
      pending_count: 0,
      sub_waitlist_count: 0,
      sort_order: 1,
      created_at: '2029-06-15T18:00:00Z',
      updated_at: '2029-06-15T18:00:00Z',
    }],
    created_at: '2029-06-15T18:00:00Z',
    updated_at: '2029-06-15T18:00:00Z',
    ...overrides.post,
  }
  const [statusLabel, statusTone] = postStatus(post.post_status, bucket, isOwner)
  return {
    bucket,
    can_view_detail: canViewDetail,
    post,
    is_owner: isOwner,
    request_id: isOwner ? null : uuid(),
    request_status: isOwner ? null : 'confirmed',
    status_label: statusLabel,
    status_tone: statusTone,
    ...overrides.card,
  }
}

export function page(items = [], { nextCursor = null, limit = 40 } = {}) {
  return { items, next_cursor: nextCursor, has_more: Boolean(nextCursor), limit }
}

// Answer each list request with `answers[endpoint]`, which may be a value, an
// Error to reject with, or a function of the request's view and cursor.
export function fakePageApi(answers = {}) {
  const allAnswers = { [GAMES]: page(), [NEED_A_SUB]: page(), ...answers }
  vi.mocked(apiRequest).mockImplementation((path, options) => {
    const endpoint = endpointFor(path, options?.method || 'GET')
    const answer = allAnswers[endpoint]
    if (answer === undefined) throw new Error(`No fake answer for ${endpoint}`)
    const query = new URL(path, 'http://test.local').searchParams
    const value = typeof answer === 'function'
      ? answer({ view: query.get('view'), cursor: query.get('cursor'), options })
      : answer
    if (value instanceof Error) return Promise.reject(value)
    return Promise.resolve(value)
  })
}

// Requests the page sent to an endpoint, as { view, cursor } pairs.
export function requestsTo(endpoint) {
  return vi.mocked(apiRequest).mock.calls
    .filter(([path, options]) => endpointFor(path, options?.method || 'GET') === endpoint)
    .map(([path]) => {
      const query = new URL(path, 'http://test.local').searchParams
      return { view: query.get('view'), cursor: query.get('cursor') }
    })
}

export function renderMyGames() {
  const router = createMemoryRouter([
    { path: '/my-games', element: <MyGamesPage /> },
    { path: '/games/:gameId', element: <h1>Game Details</h1> },
    { path: '/need-a-sub/posts/:postId', element: <h1>Post Detail</h1> },
  ], { initialEntries: ['/my-games'] })
  const view = render(<RouterProvider router={router} />)
  return { router, ...view }
}
