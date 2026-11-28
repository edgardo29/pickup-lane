import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, vi } from 'vitest'
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom'
import { onAuthStateChanged, signInWithPopup, createUserWithEmailAndPassword, signOut } from 'firebase/auth'
import { AuthProvider } from '../../../src/context/AuthProvider.jsx'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { auth } from '../../../src/lib/firebase.js'
import { apiRequest, ApiRequestError } from '../../../src/lib/apiClient.js'
import { CreateAccountPage } from '../../../src/pages/auth/CreateAccountPage.jsx'
import { FinishProfilePage } from '../../../src/pages/auth/FinishProfilePage.jsx'
import { SignInPage } from '../../../src/pages/auth/SignInPage.jsx'
import { RedirectSignedIn, SignupFlow } from '../../../src/routes/RouteGuards.jsx'
import { AuthReturnGuard } from '../../../src/routes/AuthReturnGuard.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import fields from './backend_fields.json'

vi.mock('firebase/auth', async (original) => ({ ...(await original()), onAuthStateChanged: vi.fn(), signInWithPopup: vi.fn(), createUserWithEmailAndPassword: vi.fn(), signOut: vi.fn() }))
vi.mock('../../../src/lib/firebase.js', () => ({ auth: { currentUser: null }, ensureAuthPersistence: vi.fn().mockResolvedValue(undefined) }))
vi.mock('../../../src/lib/apiClient.js', async (original) => ({ ...(await original()), apiRequest: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

export const USER_ID = '00000000-0000-4000-8000-000000000011'
export const GAME_ID = '00000000-0000-4000-8000-000000000021'
export const NOW = '2026-06-15T17:00:00Z'
export const GAME_PATH = `/games/${GAME_ID}?intent=join`
export const EMAIL = 'signup@example.test'
export const PASSWORD = 'synthetic-pass-1'
export function account(overrides = {}) {
  return { id: USER_ID, role: 'player', email: EMAIL, email_verified_at: NOW, phone: null,
    first_name: 'Jordan', last_name: 'Player', date_of_birth: '1990-01-01', profile_photo_url: null,
    home_city: null, home_state: null, account_status: 'active', hosting_status: 'eligible', member_since: NOW, ...overrides }
}
export function unfinished(overrides = {}) { return account({ first_name: null, last_name: null, date_of_birth: null, ...overrides }) }
export function firebaseUser(uid = 'synthetic-f05-user') { return { uid, email: EMAIL, displayName: null, emailVerified: true, getIdToken: vi.fn().mockResolvedValue(`synthetic-${uid}`) } }
export const server = {}
let onUser
export const sdkGoogle = signInWithPopup
export const sdkCreate = createUserWithEmailAndPassword
export const sdkSignOut = signOut
export const http = apiRequest
export const firebaseAuth = auth
export function error(message, status = 503) { return new ApiRequestError(message, { status, code: status === 404 ? 'API.NOT_FOUND' : 'API.SERVICE_UNAVAILABLE' }) }
export function firebaseError(code) { return Object.assign(new Error(code), { code }) }
export function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
export async function settle(request, value, reject = false) { await act(async () => request[reject ? 'reject' : 'resolve'](value)) }
export function credentialWhenReady(request) { return request.promise.then((credential) => { auth.currentUser = credential.user; onUser(credential.user); return credential }) }
export async function emit(user) { auth.currentUser = user; await act(async () => onUser(user)) }
export function count(path, method = 'GET') { return vi.mocked(http).mock.calls.filter(([p, o]) => p.split('?')[0] === path && (o?.method || 'GET') === method).length }

function fakeApi(path, options = {}) {
  if (path.startsWith('/auth/email-availability?')) {
    if (server.availabilityError) return Promise.reject(server.availabilityError)
    return Promise.resolve({ email: new URL(path, 'https://test.invalid').searchParams.get('email').trim().toLowerCase(), available: server.available })
  }
  if (path === '/auth/me') {
    if (server.accountError) return Promise.reject(server.accountError)
    return server.account ? Promise.resolve(server.account) : Promise.reject(error('User not found.', 404))
  }
  if (path === '/auth/sync-user') { server.account ||= unfinished(); return Promise.resolve(server.account) }
  if (path === '/users/me') { if (server.profileError) return Promise.reject(server.profileError); server.account = { ...server.account, ...JSON.parse(options.body) }; return Promise.resolve(server.account) }
  if (path === '/auth/unfinished-account') {
    if (server.cleanupError) return Promise.reject(server.cleanupError)
    if (server.account?.first_name && server.account.last_name && server.account.date_of_birth) return Promise.reject(error('Completed accounts must use account deletion.', 409))
    server.account = null; return Promise.resolve(undefined)
  }
  if (path.startsWith('/games/')) {
    if (server.returnError) return Promise.reject(server.returnError)
    return Promise.resolve(game())
  }
  return Promise.reject(error(`Unexpected ${options.method || 'GET'} ${path}`, 500))
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] }); vi.setSystemTime(new Date(NOW))
  window.localStorage.clear(); window.sessionStorage.clear()
  vi.stubGlobal('scrollTo', vi.fn())
  Object.keys(server).forEach((key) => delete server[key])
  server.account = null; server.available = true; auth.currentUser = null
  vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => { onUser = callback; queueMicrotask(() => callback(auth.currentUser)); return () => { onUser = () => {} } })
  const credential = async () => { const user = firebaseUser(); auth.currentUser = user; onUser(user); return { user } }
  vi.mocked(sdkGoogle).mockImplementation(credential)
  vi.mocked(sdkCreate).mockImplementation(credential)
  vi.mocked(sdkSignOut).mockImplementation(async () => { auth.currentUser = null; onUser(null) })
  vi.mocked(http).mockImplementation(fakeApi)
})
afterEach(() => {
  vi.mocked(http).mock.calls.forEach(([path, options], index) => {
    const result = vi.mocked(http).mock.settledResults[index]
    if (result?.type !== 'fulfilled') return
    if (path === '/auth/unfinished-account') { expect(result.value).toBeUndefined(); return }
    const route = path.startsWith('/games/') ? '/games/{game_id}' : path.split('?')[0]
    checkBackendAnswer(fields, `${options?.method || 'GET'} ${route}`, result.value)
  })
})
function Destination() { const location = useLocation(); return <h1>Destination {location.pathname}{location.search}</h1> }
function Session() { const { appUser, pendingSignup, isLoading } = useAuth(); return <><output aria-label="Current account">{isLoading ? 'Loading' : appUser?.email || 'Signed out'}</output><output aria-label="Signup draft">{pendingSignup ? 'Pending' : 'Empty'}</output></> }
export function renderSignup({ from, path = '/create-account', initialUser = null } = {}) {
  auth.currentUser = initialUser
  const router = createMemoryRouter([
    { element: <SignupFlow />, children: [
      { path: '/create-account', element: <RedirectSignedIn><CreateAccountPage /></RedirectSignedIn> },
      { path: '/finish-profile', element: <FinishProfilePage /> },
    ] },
    { path: '/sign-in', element: <RedirectSignedIn><SignInPage /></RedirectSignedIn> },
    { path: '/games/:gameId', element: <AuthReturnGuard><Destination /></AuthReturnGuard> },
    { path: '*', element: <Destination /> },
  ], { initialEntries: [{ pathname: path, state: from === undefined ? undefined : { from } }] })
  const view = render(<AuthProvider><RouterProvider router={router} /><Session /></AuthProvider>)
  router.view = view
  return router
}
export async function ready() { await waitFor(() => expect(screen.getByRole('button', { name: 'Create Account' })).toBeEnabled()) }
export async function enterEmail(email = EMAIL, password = PASSWORD) {
  await ready(); const user = userEvent.setup()
  if (email) await user.type(screen.getByLabelText('Email'), email)
  if (password) await user.type(screen.getByLabelText(/^Password/, { selector: 'input' }), password)
  return user
}
export async function beginEmail(email = EMAIL, password = PASSWORD) { const user = await enterEmail(email, password); await user.click(screen.getByRole('button', { name: 'Create Account' })); return user }
export async function beginGoogle() { await ready(); await userEvent.setup().click(screen.getByRole('button', { name: 'Continue with Google' })) }
export async function submitProfile(birthday = '1990-01-01') {
  const user = userEvent.setup()
  await screen.findByRole('heading', { name: 'Finish Profile' })
  await waitFor(() => expect(screen.getByLabelText('First Name')).toBeEnabled())
  await user.type(screen.getByLabelText('First Name'), 'Jordan'); await user.type(screen.getByLabelText('Last Name'), 'Player')
  const [year, month, day] = birthday.split('-')
  await user.selectOptions(screen.getByLabelText('Birth year'), year)
  await user.selectOptions(screen.getByLabelText('Birth month'), month)
  await user.selectOptions(screen.getByLabelText('Birth day'), day)
  await user.click(screen.getByRole('button', { name: 'Continue' }))
}
export async function at(router, path) { await waitFor(() => expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(path)) }
export async function go(router, path) { await act(async () => router.navigate(path)) }

function game() {
  return { id: GAME_ID, game_type: 'official', payment_collection_type: 'in_app', publish_status: 'published', game_status: 'active', public_visibility_status: 'visible', join_enforcement_status: 'open', title: 'Evening Pickup', description: null,
    venue_id: '00000000-0000-4000-8000-000000000022', venue_name_snapshot: 'Central Field', address_snapshot: '100 Main St', city_snapshot: 'Chicago', state_snapshot: 'IL', neighborhood_snapshot: null,
    starts_at: '2026-06-15T23:00:00Z', ends_at: '2026-06-16T00:00:00Z', starts_on_local: '2026-06-15', timezone: 'America/Chicago', format_label: '7v7', game_player_group: 'coed', skill_level: 'all', environment_type: 'outdoor', total_spots: 14, price_per_player_cents: 1000, currency: 'USD', allow_guests: true, max_guests_per_booking: 2, waitlist_enabled: true, is_chat_enabled: true, custom_rules_text: null, custom_cancellation_text: null, game_notes: null, parking_notes: null, cancelled_at: null, cancel_reason: null, host_guest_max: 0, host_user_id: null, roster_counts: { occupied_spots: 0, spots_remaining: 14, waitlist_count: 0 } }
}
