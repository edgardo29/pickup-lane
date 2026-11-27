import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, vi } from 'vitest'
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom'
import { onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, createUserWithEmailAndPassword, signOut } from 'firebase/auth'
import { AuthProvider } from '../../../src/context/AuthProvider.jsx'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { auth } from '../../../src/lib/firebase.js'
import { apiRequest, ApiRequestError } from '../../../src/lib/apiClient.js'
import { SignInPage } from '../../../src/pages/auth/SignInPage.jsx'
import { CreateAccountPage } from '../../../src/pages/auth/CreateAccountPage.jsx'
import { FinishProfilePage } from '../../../src/pages/auth/FinishProfilePage.jsx'
import { ForgotPasswordPage } from '../../../src/pages/auth/ForgotPasswordPage.jsx'
import CreateGamePage from '../../../src/pages/create-game/CreateGamePage.jsx'
import GameCheckoutPage from '../../../src/pages/browse-games/GameCheckoutPage.jsx'
import NeedASubEditPage from '../../../src/pages/need-a-sub/NeedASubEditPage.jsx'
import NeedASubPublishSuccessPage from '../../../src/pages/need-a-sub/NeedASubPublishSuccessPage.jsx'
import AccountSuspendedPage from '../../../src/pages/account-suspended/AccountSuspendedPage.jsx'
import { RedirectSignedIn, RequireAppUser, RequireSuspendedAppUser } from '../../../src/routes/RouteGuards.jsx'
import { AuthReturnGuard } from '../../../src/routes/AuthReturnGuard.jsx'
import { AppRoutes } from '../../../src/routes/AppRoutes.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import fields from './backend_fields.json'

vi.mock('firebase/auth', async (original) => ({ ...(await original()), onAuthStateChanged: vi.fn(), signInWithEmailAndPassword: vi.fn(), signInWithPopup: vi.fn(), createUserWithEmailAndPassword: vi.fn(), signOut: vi.fn() }))
vi.mock('../../../src/lib/firebase.js', () => ({ auth: { currentUser: null }, ensureAuthPersistence: vi.fn().mockResolvedValue(undefined) }))
vi.mock('../../../src/lib/apiClient.js', async (original) => ({ ...(await original()), apiRequest: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({ stripePromise: Promise.resolve(null), areStripePaymentsEnabled: () => false, hasStripeCheckoutSupport: () => false }))

export const USER_ID = '00000000-0000-4000-8000-000000000011'
export const GAME_ID = '00000000-0000-4000-8000-000000000021'
const VENUE_ID = '00000000-0000-4000-8000-000000000022'
const HOST_ID = USER_ID
export const POST_ID = '00000000-0000-4000-8000-000000000031'
export const NOW = '2026-06-15T17:00:00Z'
export const GAME_PATH = `/games/${GAME_ID}/checkout?intent=join`
export function account(overrides = {}) {
  return { id: USER_ID, role: 'player', email: 'signin@example.test', email_verified_at: NOW,
    phone: null, first_name: 'Jordan', last_name: 'Player', date_of_birth: '1990-01-01',
    profile_photo_url: null, home_city: null, home_state: null, account_status: 'active',
    hosting_status: 'eligible', member_since: NOW, ...overrides }
}
export function unfinished(overrides = {}) { return account({ first_name: null, last_name: null, date_of_birth: null, ...overrides }) }
export function firebaseUser(uid = 'synthetic-f07-user') { return { uid, email: 'signin@example.test', displayName: null, emailVerified: true, getIdToken: vi.fn().mockResolvedValue(`synthetic-${uid}`) } }
export const server = {}
let onUser
export const firebaseAuth = auth
export const sdkEmail = signInWithEmailAndPassword
export const sdkGoogle = signInWithPopup
export const sdkCreate = createUserWithEmailAndPassword
export const http = apiRequest
export function error(message, status = 503, code = '') { return new ApiRequestError(message, { status, code: code || ({ 404: 'API.NOT_FOUND', 503: 'API.SERVICE_UNAVAILABLE' }[status] || '') }) }
export function firebaseError(code) { return Object.assign(new Error(code), { code }) }
export function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
export async function settle(request, value, reject = false) { await act(async () => request[reject ? 'reject' : 'resolve'](value)) }
// Firebase publishes its current user before returning a successful credential.
export function credentialWhenReady(request) {
  return request.promise.then((credential) => {
    auth.currentUser = credential.user
    onUser(credential.user)
    return credential
  })
}
export async function emit(user) { auth.currentUser = user; await act(async () => onUser(user)) }
export function notice() { return { account_status: 'suspended', notice_title: 'Account suspended', notice_message: 'Pickup Lane suspended this account. Contact support if this was a mistake.', notice_occurred_at: NOW } }

export function fakeApi(path, options = {}) {
  if (path === '/auth/me') {
    if (server.accountError) return Promise.reject(server.accountError)
    if (!server.account) return Promise.reject(error('User not found.', 404, 'API.NOT_FOUND'))
    return Promise.resolve(server.account)
  }
  if (path === '/auth/sync-user') { server.account ||= unfinished(); return Promise.resolve(server.account) }
  if (path === '/users/me') { server.account = { ...server.account, ...JSON.parse(options.body) }; return Promise.resolve(server.account) }
  if (path === '/account-suspended') {
    if (server.noticeError) return Promise.reject(server.noticeError)
    return Promise.resolve(server.notice)
  }
  if (path.startsWith('/venues/')) return Promise.resolve(venue())
  if (path.startsWith('/community-game-details/')) return Promise.resolve(communityDetails())
  if (path.startsWith('/game-images?')) return Promise.resolve([])
  if (/^\/games\/[^/]+\/participants/.test(path)) return Promise.resolve(checkoutParticipants())
  if (path.startsWith('/games/') && server.gameOverrides?.public_visibility_status === 'hidden' && !options.headers?.Authorization) return Promise.reject(error('Game not found.', 404))
  if (path.startsWith('/games/')) return server.returnError ? Promise.reject(server.returnError) : Promise.resolve(game({ game_type: 'community', payment_collection_type: 'external_host', ...server.gameOverrides, host_user_id: options.headers?.Authorization && !server.resourceOwner ? USER_ID : null }))
  if (path.startsWith('/need-a-sub/posts/')) return server.returnError ? Promise.reject(server.returnError) : Promise.resolve({ ...post(), ...server.postOverrides, ...(server.resourceOwner ? { owner_user_id: server.resourceOwner } : {}) })
  return Promise.reject(error(`Unexpected ${options.method || 'GET'} ${path}`, 500))
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(NOW))
  window.localStorage.clear()
  vi.stubGlobal('scrollTo', vi.fn())
  Object.keys(server).forEach((key) => delete server[key])
  server.account = account()
  server.notice = notice()
  auth.currentUser = null
  vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => { onUser = callback; queueMicrotask(() => callback(auth.currentUser)); return () => { onUser = () => {} } })
  const credential = async () => { const user = firebaseUser(); auth.currentUser = user; onUser(user); return { user } }
  vi.mocked(sdkEmail).mockImplementation(credential)
  vi.mocked(sdkGoogle).mockImplementation(credential)
  vi.mocked(signOut).mockImplementation(async () => { auth.currentUser = null; onUser(null) })
  vi.mocked(http).mockImplementation(fakeApi)
})
afterEach(() => {
  vi.mocked(http).mock.calls.forEach(([path, options], index) => {
    const result = vi.mocked(http).mock.settledResults[index]
    if (result?.type === 'fulfilled') {
      const route = path.startsWith('/game-images?') ? '/game-images' : /^\/games\/[^/]+\/participants/.test(path) ? '/games/{game_id}/participants' : path.startsWith('/venues/') ? '/venues/{venue_id}' : path.startsWith('/community-game-details/') ? '/community-game-details/games/{game_id}/host-edit' : path.startsWith('/games/') ? '/games/{game_id}' : path.startsWith('/need-a-sub/posts/') ? '/need-a-sub/posts/{sub_post_id}' : path
      checkBackendAnswer(fields, `${options?.method || 'GET'} ${route}`, result.value)
    }
  })
})

// The target reads only router/session state. The tests prove authentication
// navigation here; the destination pages retain their own feature tests.
function Destination() { const location = useLocation(); return <h1>Destination {location.pathname}{location.search}</h1> }
function Session() { const { appUser, isLoading } = useAuth(); return <output aria-label="Current account">{isLoading ? 'Loading' : appUser?.email || 'Signed out'}</output> }
export function renderSignIn({ from, path = '/sign-in', initialUser = null, realRoutes = false, realDestination = '' } = {}) {
  auth.currentUser = initialUser
  const entries = [{ pathname: path.split('?')[0], search: path.includes('?') ? `?${path.split('?')[1]}` : '', state: from === undefined ? undefined : { from } }]
  const routes = realRoutes ? [{ path: '*', element: <AppRoutes /> }] : [
    { path: '/sign-in', element: <RedirectSignedIn><SignInPage /></RedirectSignedIn> },
    { path: '/create-account', element: <RedirectSignedIn><CreateAccountPage /></RedirectSignedIn> },
    { path: '/finish-profile', element: <FinishProfilePage /> },
    { path: '/forgot-password', element: <ForgotPasswordPage /> },
    { path: '/account-suspended', element: <RequireSuspendedAppUser><AccountSuspendedPage /></RequireSuspendedAppUser> },
    { path: '/games/:gameId/checkout', element: <RequireAppUser><AuthReturnGuard>{realDestination === 'checkout' ? <GameCheckoutPage /> : <Destination />}</AuthReturnGuard></RequireAppUser> },
    { path: '/games/:gameId', element: <AuthReturnGuard><Destination /></AuthReturnGuard> },
    { path: '/games/:gameId/edit', element: <RequireAppUser><AuthReturnGuard><CreateGamePage /></AuthReturnGuard></RequireAppUser> },
    { path: '/need-a-sub/posts/:postId', element: <AuthReturnGuard><Destination /></AuthReturnGuard> },
    { path: '/need-a-sub/posts/:postId/edit', element: <RequireAppUser><AuthReturnGuard>{realDestination === 'post edit' ? <NeedASubEditPage /> : <Destination />}</AuthReturnGuard></RequireAppUser> },
    { path: '/need-a-sub/posts/:postId/published', element: <RequireAppUser><AuthReturnGuard>{realDestination === 'publication' ? <NeedASubPublishSuccessPage /> : <Destination />}</AuthReturnGuard></RequireAppUser> },
    { path: '*', element: <Destination /> },
  ]
  const router = createMemoryRouter(routes, { initialEntries: entries })
  render(<AuthProvider><RouterProvider router={router} /><Session /></AuthProvider>)
  return router
}
export async function ready() { await waitFor(() => expect(screen.getByRole('button', { name: 'Sign In' })).toBeEnabled()) }
export async function signIn(method = 'email') {
  const user = userEvent.setup()
  await ready()
  if (method === 'email') {
    await user.type(screen.getByLabelText('Email'), 'signin@example.test')
    await user.type(screen.getByLabelText(/^Password/, { selector: 'input' }), 'synthetic-pass-1')
    await user.click(screen.getByRole('button', { name: 'Sign In' }))
  } else await user.click(screen.getByRole('button', { name: 'Continue with Google' }))
  return user
}
export async function finishProfile() {
  const user = userEvent.setup()
  await screen.findByRole('heading', { name: 'Finish Profile' })
  await waitFor(() => expect(screen.getByLabelText('First Name')).toBeEnabled())
  await user.type(screen.getByLabelText('First Name'), 'Jordan')
  await user.type(screen.getByLabelText('Last Name'), 'Player')
  await user.selectOptions(screen.getByLabelText('Birth month'), '01')
  await user.selectOptions(screen.getByLabelText('Birth day'), '01')
  await user.selectOptions(screen.getByLabelText('Birth year'), '1990')
  await user.click(screen.getByRole('button', { name: 'Continue' }))
}
export async function at(router, path) { await waitFor(() => expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(path)) }

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
    starts_at: '2026-06-15T23:00:00Z',
    ends_at: '2026-06-16T00:00:00Z',
    starts_on_local: '2026-06-15',
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


export function post() {
  return { id: POST_ID, owner_user_id: USER_ID, post_status: 'active', public_visibility_status: 'visible', sport_type: 'soccer', format_label: '7v7', environment_type: 'outdoor', skill_level: 'intermediate', game_player_group: 'coed', team_name: null,
    starts_at: '2026-06-15T23:00:00Z', ends_at: '2026-06-16T00:00:00Z', timezone: 'America/Chicago', location_name: 'Test Field', address_line_1: '200 Test Avenue', city: 'Chicago', state: 'IL', postal_code: '60601', country_code: 'US', neighborhood: null, subs_needed: 1, price_due_at_venue_cents: 0, currency: 'USD', payment_note: null, notes: null, expires_at: '2026-06-15T23:00:00Z', filled_at: null, canceled_at: null, canceled_by_user_id: null, cancel_reason: null, removed_at: null, removed_by_user_id: null, remove_reason: null, created_at: NOW, updated_at: NOW, pending_count: 0, confirmed_count: 0, sub_waitlist_count: 0,
    positions: [{ id: '00000000-0000-4000-8000-000000000032', sub_post_id: POST_ID, position_label: 'field_player', player_group: 'open', spots_needed: 1, sort_order: 0, pending_count: 0, confirmed_count: 0, sub_waitlist_count: 0, created_at: NOW, updated_at: NOW }] }
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
    approved_at: '2026-06-14T18:00:00Z',
    is_active: true,
    created_at: '2026-06-14T18:00:00Z',
    updated_at: '2026-06-14T18:00:00Z',
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
    created_at: '2026-06-14T18:00:00Z',
    updated_at: '2026-06-14T18:00:00Z',
    ...overrides,
  }
}


function confirmedParticipant() {
  return {
    id: '00000000-0000-4000-8000-000000000051', game_id: GAME_ID,
    booking_id: '00000000-0000-4000-8000-000000000052',
    participant_type: 'registered_user', user_id: USER_ID, guest_of_user_id: null,
    display_name_snapshot: 'Jordan Player', participant_status: 'confirmed',
    cancellation_type: 'none', roster_order: 1, joined_at: NOW, confirmed_at: NOW,
    cancelled_at: null,
  }
}

function checkoutParticipants() {
  const player = confirmedParticipant()
  // The hidden community game still has its host and all three roster places.
  return [
    { ...player, id: '00000000-0000-4000-8000-000000000054', booking_id: null,
      participant_type: 'host', user_id: server.resourceOwner || HOST_ID,
      display_name_snapshot: 'Test Host', roster_order: 1 },
    { ...player, roster_order: 2 },
    { ...player, id: '00000000-0000-4000-8000-000000000055',
      booking_id: '00000000-0000-4000-8000-000000000056',
      user_id: '00000000-0000-4000-8000-000000000098',
      display_name_snapshot: 'Other Player', roster_order: 3 },
  ]
}
