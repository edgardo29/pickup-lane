// Helpers for Need a Sub tests: fake API answers, the signed-in state, and the
// page with the routes a visitor moves through (post detail, Sign In, Create
// Account, Finish Profile, and game discovery).
//
// Each test file must also mock the API client, the auth hook, and the nav bar:
//   vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
//     ...(await importOriginal()),
//     apiRequest: vi.fn(),
//   }))
//   vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
//   vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
//   vi.mock('../../../src/context/authProviderHelpers.js', () => ({
//     waitForCurrentFirebaseUser: vi.fn(),
//   }))
// The last one keeps Firebase itself out of the tests; Finish Profile waits on
// it for the newly created account.

import { act, render, screen } from '@testing-library/react'
import { useSyncExternalStore } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import { CreateAccountPage } from '../../../src/pages/auth/CreateAccountPage.jsx'
import { FinishProfilePage } from '../../../src/pages/auth/FinishProfilePage.jsx'
import { SignInPage } from '../../../src/pages/auth/SignInPage.jsx'
import NeedASubDetailPage from '../../../src/pages/need-a-sub/NeedASubDetailPage.jsx'
import NeedASubPage from '../../../src/pages/need-a-sub/NeedASubPage.jsx'
import { RedirectSignedIn } from '../../../src/routes/RouteGuards.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

// Noon in Chicago on 2026-06-15. Tests fake only the clock (Date), so the page's
// timers and promises still run normally.
export const NOW = '2026-06-15T17:00:00Z'
export const TODAY = '2026-06-15'
export const TOMORROW = '2026-06-16'

export const CARDS = 'GET /need-a-sub/posts/cards'
export const POST_DETAIL = 'GET /need-a-sub/posts/{sub_post_id}'
export const MY_REQUESTS = 'GET /need-a-sub/my-requests'
export const REQUEST_SPOT = 'POST /need-a-sub/posts/{sub_post_id}/requests'
export const EMAIL_AVAILABILITY = 'GET /auth/email-availability'
export const SAVE_PROFILE = 'PATCH /users/me'

export const VIEWER_ID = '00000000-0000-4000-8000-0000000000a1'
export const OWNER_ID = '00000000-0000-4000-8000-0000000000a2'

function endpointFor(path, method = 'GET') {
  const pathname = new URL(path, 'http://test.local').pathname
  if (/^\/need-a-sub\/posts\/(cards)$/.test(pathname)) return CARDS
  if (/^\/need-a-sub\/posts\/[^/]+$/.test(pathname)) return `${method} /need-a-sub/posts/{sub_post_id}`
  if (/^\/need-a-sub\/posts\/[^/]+\/requests$/.test(pathname)) {
    return `${method} /need-a-sub/posts/{sub_post_id}/requests`
  }
  return `${method} ${pathname}`
}

// After each test, check every answer the fake API gave the page against the
// fields the backend really sends. Failed and still-waiting requests are skipped.
afterEach(() => {
  const mockedRequest = vi.mocked(apiRequest)
  mockedRequest.mock.calls.forEach(([path, options], index) => {
    const result = mockedRequest.mock.settledResults[index]
    if (result?.type === 'fulfilled') {
      checkBackendAnswer(backendFields, endpointFor(path, options?.method || 'GET'), result.value)
    }
  })
})

// Answer each endpoint from `answers`: a value, an Error to reject with, a
// promise to control timing, or a function (path, options) returning one.
export function fakeApi(answers = {}) {
  vi.mocked(apiRequest).mockImplementation(async (path, options = {}) => {
    const endpoint = endpointFor(path, options.method || 'GET')
    if (!(endpoint in answers)) {
      throw new Error(`No fake answer for ${endpoint}`)
    }
    const answer = typeof answers[endpoint] === 'function'
      ? answers[endpoint](path, options)
      : answers[endpoint]
    if (answer instanceof Error) {
      throw answer
    }
    return answer
  })
}

// The card list requests the page made, as { view, startsOn, cursor, signedIn }.
export function cardRequests() {
  return vi.mocked(apiRequest).mock.calls
    .filter(([path]) => endpointFor(path) === CARDS)
    .map(([path, options]) => {
      const params = new URL(path, 'http://test.local').searchParams
      return {
        cursor: params.get('cursor'),
        signedIn: Boolean(options?.headers?.Authorization),
        startsOn: params.get('starts_on'),
        view: params.get('view'),
      }
    })
}

// A promise the test resolves or rejects later, to control answer timing.
export function deferred() {
  let resolve
  let reject
  const promise = new Promise((promiseResolve, promiseReject) => {
    resolve = promiseResolve
    reject = promiseReject
  })
  return { promise, reject, resolve }
}

let nextNumber = 1

function uuid(number) {
  return `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`
}

// One sub need as the API returns it. Default: two Any field players, none filled.
export function position(overrides = {}) {
  return {
    id: uuid(nextNumber++),
    sub_post_id: uuid(0),
    position_label: 'field_player',
    player_group: 'open',
    spots_needed: 2,
    sort_order: 0,
    pending_count: 0,
    confirmed_count: 0,
    sub_waitlist_count: 0,
    created_at: '2026-06-14T15:00:00Z',
    updated_at: '2026-06-14T15:00:00Z',
    ...overrides,
  }
}

// One card as the list returns it (the public summary). Default: a 6:00 PM
// coed 7v7 outdoor game today needing two Any field players.
export function card(overrides = {}) {
  const id = overrides.id ?? uuid(nextNumber++)
  // The server numbers a post's needs in order, starting at 0.
  const positions = (overrides.positions ?? [position()])
    .map((need, index) => ({ ...need, sub_post_id: id, sort_order: index }))
  return {
    id,
    post_status: 'active',
    public_visibility_status: 'visible',
    sport_type: 'soccer',
    format_label: '7v7',
    environment_type: 'outdoor',
    skill_level: 'intermediate',
    game_player_group: 'coed',
    starts_at: '2026-06-15T23:00:00Z',
    ends_at: '2026-06-16T01:00:00Z',
    timezone: 'America/Chicago',
    location_name: `Field ${id.slice(-3)}`,
    city: 'Chicago',
    state: 'IL',
    neighborhood: null,
    subs_needed: positions.reduce((total, need) => total + need.spots_needed, 0),
    price_due_at_venue_cents: 0,
    currency: 'USD',
    expires_at: overrides.starts_at ?? '2026-06-15T23:00:00Z',
    created_at: '2026-06-14T15:00:00Z',
    updated_at: '2026-06-14T15:00:00Z',
    pending_count: positions.reduce((total, need) => total + need.pending_count, 0),
    confirmed_count: positions.reduce((total, need) => total + need.confirmed_count, 0),
    sub_waitlist_count: positions.reduce((total, need) => total + need.sub_waitlist_count, 0),
    ...overrides,
    positions,
  }
}

// The full post a signed-in visitor gets from post detail.
export function fullPost(overrides = {}) {
  return {
    ...card(overrides),
    owner_user_id: OWNER_ID,
    team_name: null,
    address_line_1: '200 Test Avenue',
    postal_code: '60601',
    country_code: 'US',
    payment_note: null,
    notes: 'Bring a white and a dark shirt.',
    filled_at: null,
    canceled_at: null,
    canceled_by_user_id: null,
    cancel_reason: null,
    removed_at: null,
    removed_by_user_id: null,
    remove_reason: null,
    ...overrides,
  }
}

// One card list answer.
export function cardPage({ posts = [], hasMore = false, nextCursor = null } = {}) {
  return { posts, next_cursor: nextCursor, has_more: hasMore, limit: 40 }
}

// The Pickup Lane account as the sign-in state holds it.
export function appUser(overrides = {}) {
  return {
    id: VIEWER_ID,
    role: 'player',
    email: 'player@example.test',
    email_verified_at: '2026-01-02T15:00:00Z',
    phone: null,
    first_name: 'Taylor',
    last_name: 'Player',
    date_of_birth: '1990-01-01',
    profile_photo_url: null,
    home_city: null,
    home_state: null,
    account_status: 'active',
    hosting_status: 'not_eligible',
    member_since: '2026-01-02T15:00:00Z',
    ...overrides,
  }
}

function firebaseUser() {
  return { displayName: null, getIdToken: vi.fn(async () => 'test-id-token'), uid: 'firebase-viewer' }
}

// The current sign-in state. Tests change it with signedOut(), signedIn(), or
// signedInWithoutAccount(); sign-in actions change it the way signing in does.
// Like the real auth provider, a change re-renders every page using it.
let authState
const authListeners = new Set()

function subscribeToAuth(listener) {
  authListeners.add(listener)
  return () => authListeners.delete(listener)
}

function setAuth(nextState) {
  authState = nextState
  act(() => authListeners.forEach((listener) => listener()))
}

function baseAuth() {
  return {
    appUser: null,
    beginEmailSignup: vi.fn(),
    cleanupUnfinishedSignup: vi.fn(async () => {}),
    currentUser: null,
    isLoading: false,
    pendingGoogleSignup: false,
    pendingSignup: null,
    settleGoogleSignupRedirect: vi.fn(),
    signInWithEmail: vi.fn(),
    signInWithGoogle: vi.fn(),
    signUpWithEmail: vi.fn(),
    syncCurrentFirebaseUser: vi.fn(),
    updateAppUser: vi.fn(),
  }
}

function setFakeAuth(state) {
  authState = state
  vi.mocked(useAuth).mockImplementation(() => useSyncExternalStore(subscribeToAuth, () => authState))
  return authState
}

export function signedOut() {
  return setFakeAuth(baseAuth())
}

export function signedIn(overrides = {}) {
  return setFakeAuth({ ...baseAuth(), appUser: appUser(overrides), currentUser: firebaseUser() })
}

// Signed in to Firebase, but with no finished Pickup Lane account.
export function signedInWithoutAccount() {
  return setFakeAuth({ ...baseAuth(), currentUser: firebaseUser() })
}

// Make the state signed in, as a successful sign-in or sign-up does.
export function completeSignIn(user = appUser()) {
  setAuth({ ...authState, appUser: user, currentUser: firebaseUser(), pendingSignup: null })
  return user
}

// Change part of the sign-in state, as an auth action does.
export function updateAuth(changes) {
  setAuth({ ...authState, ...changes })
}

export function currentAuth() {
  return authState
}

// Render Need a Sub at `path`.
export function renderNeedASub(path = '/need-a-sub') {
  const router = createMemoryRouter(
    [
      { path: '/need-a-sub', element: <NeedASubPage /> },
      { path: '/need-a-sub/posts/:postId', element: <NeedASubDetailPage /> },
      { path: '/sign-in', element: <RedirectSignedIn><SignInPage /></RedirectSignedIn> },
      { path: '/create-account', element: <RedirectSignedIn><CreateAccountPage /></RedirectSignedIn> },
      { path: '/finish-profile', element: <FinishProfilePage /> },
      { path: '/games', element: <h1>Game discovery</h1> },
    ],
    { initialEntries: [path] },
  )
  render(<RouterProvider router={router} />)
  return router
}

// The post cards on the page, by the venue each shows.
export async function findCards() {
  return screen.findAllByRole('button', { name: /^Need \d+ Subs?/ })
}

// The venues of the shown cards, in page order, from the names a test used.
export function cardVenues(venueNames) {
  return screen.queryAllByRole('button', { name: /^Need \d+ Subs?/ })
    .map((element) => venueNames.find((name) => element.textContent.includes(name)))
}
