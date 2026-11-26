import { act, render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, vi } from 'vitest'
import { applyActionCode, sendEmailVerification } from 'firebase/auth'
import { auth } from '../../../src/lib/firebase.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import { RequireAppUser } from '../../../src/routes/RouteGuards.jsx'
import { AuthContext } from '../../../src/context/authContext.js'
import { useAuthProviderValue } from '../../../src/context/useAuthProviderValue.js'
import { createRef, useEffect, useState } from 'react'
import { ResetPasswordPage } from '../../../src/pages/auth/ResetPasswordPage.jsx'
import CreateGamePage from '../../../src/pages/create-game/CreateGamePage.jsx'
import NeedASubPage from '../../../src/pages/need-a-sub/NeedASubPage.jsx'
import BrowseGamesPage from '../../../src/pages/browse-games/BrowseGamesPage.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

vi.mock('firebase/auth', async (original) => ({ ...(await original()), applyActionCode: vi.fn(), sendEmailVerification: vi.fn(), onAuthStateChanged: vi.fn((_auth, onUser) => { queueMicrotask(() => onUser(null)); return () => {} }) }))
vi.mock('../../../src/lib/firebase.js', () => ({ auth: { currentUser: null }, ensureAuthPersistence: vi.fn() }))
vi.mock('../../../src/lib/apiClient.js', async (original) => ({ ...(await original()), apiRequest: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))
vi.mock('../../../src/lib/stripe.js', () => ({ stripePromise: Promise.resolve(null) }))

export const USER_ID = '00000000-0000-4000-8000-000000000011'
export const UID = 'synthetic-verification-user'
export const VERIFIED_AT = '2026-06-15T17:00:00Z'
export const origins = ['/create-game', '/need-a-sub?panel=create']
export const server = { verified: false, everVerified: false }
export function account(overrides = {}) {
  return { id: auth.currentUser?.uid === UID ? USER_ID : '00000000-0000-4000-8000-000000000012', role: 'player', email: 'verification@example.test',
    email_verified_at: server.verified ? VERIFIED_AT : null, phone: null,
    first_name: 'Test', last_name: 'Player', date_of_birth: '1990-01-01',
    profile_photo_url: null, home_city: null, home_state: null,
    account_status: 'active', hosting_status: server.verified || server.everVerified ? 'eligible' : 'not_eligible',
    member_since: '2026-01-01T00:00:00Z', ...overrides }
}
export function subPage() {
  const id = '00000000-0000-4000-8000-000000000021'
  return { limit: 40, next_cursor: null, has_more: false, posts: [{
    id, post_status: 'active', public_visibility_status: 'visible', sport_type: 'soccer',
    format_label: '7v7', environment_type: 'outdoor', skill_level: 'any', game_player_group: 'coed',
    starts_at: '2026-06-15T23:00:00Z', ends_at: '2026-06-16T00:00:00Z', timezone: 'America/Chicago',
    location_name: 'Public Sub Field', city: 'Chicago', state: 'IL', neighborhood: null,
    subs_needed: 1, price_due_at_venue_cents: 0, currency: 'USD', expires_at: '2026-06-15T23:00:00Z',
    created_at: VERIFIED_AT, updated_at: VERIFIED_AT,
    pending_count: 0, confirmed_count: 0, sub_waitlist_count: 0,
    positions: [{ id: '00000000-0000-4000-8000-000000000022', sub_post_id: id,
      position_label: 'field_player', player_group: 'open', spots_needed: 1, sort_order: 0,
      pending_count: 0, confirmed_count: 0, sub_waitlist_count: 0, created_at: VERIFIED_AT, updated_at: VERIFIED_AT }],
  }] }
}
export function gamePage(date) {
  const game = {
    id: '00000000-0000-4000-8000-000000000031', game_type: 'official', game_status: 'active',
    title: 'Public Game Field', display_title: 'Public Game Field', venue_name_snapshot: 'Public Game Field',
    city_snapshot: 'Chicago', state_snapshot: 'IL', location_label: 'Chicago, IL',
    starts_at: `${date}T23:00:00Z`, ends_at: `${date}T23:59:00Z`, starts_on_local: date,
    time_group_key: '18:00', timezone: 'America/Chicago', format_label: '7v7', game_player_group: 'coed',
    environment_type: 'outdoor', total_spots: 14, participant_count: 1,
    availability: { status: 'open', occupied_spots: 1, total_spots: 14, spots_remaining: 13 },
    price_per_player_cents: 0, currency: 'USD', price_label: 'Free', primary_image_url: null,
    registration_closes_at: `${date}T23:05:00Z`, public_visibility_status: 'visible', join_enforcement_status: 'open',
  }
  return { browse_today: '2026-06-15', browse_timezone: 'America/Chicago', minimum_browse_date: '2026-06-15',
    maximum_browse_date: '2026-06-28', browse_date: date, games: [game],
    time_groups: [{ group_key: '18:00', total_games: 1 }], next_cursor: null, has_more: false, limit: 40 }
}
export function fakeApi(path, options = {}) {
  const url = new URL(path, window.location.origin)
  if (url.pathname === '/auth/me' || url.pathname === '/auth/sync-user') { server.everVerified ||= server.verified; return Promise.resolve(account()) }
  if (url.pathname === '/user-payment-methods' || url.pathname === '/host-publish-fees/me') return Promise.resolve([])
  if (url.pathname === '/need-a-sub/posts/cards') return Promise.resolve(subPage())
  if (url.pathname === '/games/browse') return Promise.resolve(gamePage(url.searchParams.get('starts_on') || '2026-06-15'))
  return Promise.reject(Object.assign(new Error(`Unexpected ${options.method || 'GET'} ${path}`), { status: 500 }))
}
export let firebaseUser
beforeEach(() => {
  window.localStorage.clear()
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(VERIFIED_AT))
  vi.stubGlobal('scrollTo', vi.fn())
  server.verified = false
  server.everVerified = false
  firebaseUser = { uid: UID, email: 'verification@example.test', emailVerified: false,
    reload: vi.fn().mockResolvedValue(undefined), getIdToken: vi.fn().mockResolvedValue('synthetic-id-token') }
  auth.currentUser = firebaseUser
  vi.mocked(apiRequest).mockImplementation(fakeApi)
  vi.mocked(applyActionCode).mockImplementation(async () => { server.verified = true; firebaseUser.emailVerified = true })
  vi.mocked(sendEmailVerification).mockResolvedValue(undefined)
})
afterEach(() => {
  vi.mocked(apiRequest).mock.calls.forEach(([path, options], index) => {
    const result = vi.mocked(apiRequest).mock.settledResults[index]
    if (result?.type === 'fulfilled') {
      const endpoint = `${options?.method || 'GET'} ${new URL(path, window.location.origin).pathname}`
      checkBackendAnswer(backendFields, endpoint, result.value)
    }
  })
  vi.useRealTimers()
})
function Authentication({ children, initialUser, user, loading, controlsRef }) {
  const [appUser, setAppUser] = useState(initialUser)
  const [currentUser, setFirebaseUser] = useState(user)
  const value = useAuthProviderValue({ appUser, firebaseUser: currentUser,
    setAppUser, setFirebaseUser, status: loading ? 'loading' : 'ready' })
  useEffect(() => { controlsRef.current = { ...value, setSession: (nextUser, nextAccount) => { setFirebaseUser(nextUser); setAppUser(nextAccount) } } }, [controlsRef, value])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function verificationUrl(destination = '/create-game', code = 'verification-code') {
  const params = new URLSearchParams({ mode: 'verifyEmail', continueUrl: `${window.location.origin}${destination}` })
  if (code) params.set('oobCode', code)
  return `/reset-password?${params}`
}
export function renderVerification({ path = verificationUrl(), verified = false, signedIn = true, loading = false } = {}) {
  server.verified = verified
  server.everVerified ||= verified
  firebaseUser.emailVerified = verified
  if (!signedIn) auth.currentUser = null
  const router = createMemoryRouter([
    { path: '/reset-password', element: <ResetPasswordPage /> },
    { path: '/create-game', element: <RequireAppUser><CreateGamePage /></RequireAppUser> },
    { path: '/need-a-sub', element: <NeedASubPage /> },
    { path: '/games/browse', element: <BrowseGamesPage /> },
    { path: '/sign-in', element: <h1>Sign In</h1> },
  ], { initialEntries: [path] })
  const user = signedIn ? firebaseUser : null
  const initialUser = signedIn ? account() : null
  const controlsRef = createRef()
  const tree = (isLoading = loading) => <Authentication initialUser={initialUser} user={user} loading={isLoading} controlsRef={controlsRef}><RouterProvider router={router} /></Authentication>
  const view = render(tree())
  return {
    router, unmount: view.unmount,
    getAppUser: () => controlsRef.current.appUser,
    refreshAccount: async () => { await act(async () => controlsRef.current.refreshCurrentUserVerification()) },
    updateAuthentication: async (isLoading) => { await act(async () => view.rerender(tree(isLoading))) },
    setSession: async (nextUser, isLoading = false) => {
      auth.currentUser = nextUser
      await act(async () => {
        controlsRef.current.setSession(nextUser, nextUser ? account() : null)
        view.rerender(tree(isLoading))
      })
    },
  }
}
export function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
export async function settle(request, value, reject = false) {
  await act(async () => request[reject ? 'reject' : 'resolve'](value))
}
export async function navigate(router, path) { await act(async () => router.navigate(path)) }
export function firebaseError(code) { return Object.assign(new Error(code), { code }) }
export async function finishUnconfirmed() { await act(async () => vi.advanceTimersByTimeAsync(1500)) }
export function controlTimers() { vi.useFakeTimers() }
export const apiRequestMock = apiRequest
export const applyCode = applyActionCode
export const firebaseAuth = auth
export const sendVerification = sendEmailVerification
