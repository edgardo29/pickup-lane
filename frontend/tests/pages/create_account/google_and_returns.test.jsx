import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { account, at, beginEmail, beginGoogle, count, credentialWhenReady, deferred, EMAIL, emit, error, firebaseError, firebaseUser, GAME_PATH, http, ready, renderSignup, sdkCreate, sdkGoogle, server, settle, unfinished } from './createAccountTestKit.jsx'

it.each([undefined, GAME_PATH])('F05-2: existing Google signup opens its destination or discovery (%s)', async (from) => {
  server.account = account(); const router = renderSignup({ from }); await beginGoogle(); await at(router, from || '/games')
  expect(sdkGoogle).toHaveBeenCalledTimes(1); expect(sdkCreate).not.toHaveBeenCalled()
  expect(count('/auth/sync-user', 'POST')).toBe(0)
})
it.each([null, unfinished()])('F05-3: new or incomplete Google signup retains the destination (%j)', async (existing) => {
  server.account = existing; const router = renderSignup({ from: GAME_PATH }); await beginGoogle(); await at(router, '/finish-profile')
  expect(router.state.location.state.from).toBe(GAME_PATH)
  expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
})
it('F05-7: Google cancellation leaves a recoverable signup error', async () => {
  sdkGoogle.mockRejectedValueOnce(firebaseError('auth/popup-closed-by-user'))
  const router = renderSignup(); await beginGoogle()
  expect(await screen.findByRole('alert')).toHaveTextContent('Sign-in was cancelled before it finished.')
  expect(router.state.location.pathname).toBe('/create-account'); expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeEnabled()
})
it.each(['firebase', 'account'])('F05-7: Google connection failure permits retry (%s)', async (source) => {
  server.account = account()
  if (source === 'firebase') sdkGoogle.mockRejectedValueOnce(firebaseError('auth/network-request-failed'))
  else server.accountError = error('Could not read the account.')
  const router = renderSignup(); await beginGoogle()
  expect(await screen.findByRole('alert')).toBeInTheDocument(); await ready()
  expect(router.state.location.pathname).toBe('/create-account')
  server.accountError = null; await beginGoogle(); await at(router, '/games')
})
it.each([undefined, GAME_PATH])('F05-9: an already signed-in complete account uses its destination (%s)', async (from) => {
  server.account = account(); const router = renderSignup({ from, initialUser: firebaseUser() }); await at(router, from || '/games')
})
it('F05-9: an already signed-in incomplete account keeps its destination', async () => {
  server.account = unfinished(); const router = renderSignup({ from: GAME_PATH, initialUser: firebaseUser() }); await at(router, '/finish-profile')
  expect(router.state.location.state.from).toBe(GAME_PATH)
})
it('F05-9: an already signed-in suspended account sees its restricted destination', async () => {
  server.account = account({ account_status: 'suspended' }); const router = renderSignup({ from: GAME_PATH, initialUser: firebaseUser() }); await at(router, '/account-suspended')
})
it.each(['google', 'account'])('F05-2, F05-3, F05-7: pending Google signup disables both methods (%s)', async (source) => {
  server.account = account(); const request = deferred()
  if (source === 'google') sdkGoogle.mockReturnValueOnce(credentialWhenReady(request))
  else http.mockImplementation((path) => path === '/auth/me' ? request.promise : Promise.reject(error('Unexpected request', 500)))
  const router = renderSignup(); await beginGoogle()
  const button = screen.getByRole('button', { name: 'Checking...' })
  expect(button).toBeDisabled(); expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeDisabled()
  fireEvent.submit(button.closest('form')); expect(count('/auth/email-availability')).toBe(0); expect(sdkGoogle).toHaveBeenCalledTimes(1)
  await settle(request, source === 'google' ? { user: firebaseUser() } : account()); await at(router, '/games')
})
it.each(['complete', 'incomplete', 'new'])('F05-2, F05-3: Google completion navigates only once (%s)', async (state) => {
  server.account = state === 'complete' ? account() : state === 'incomplete' ? unfinished() : null
  const router = renderSignup({ from: GAME_PATH }); const destination = state === 'complete' ? GAME_PATH : '/finish-profile'; const arrivals = new Set()
  router.subscribe(({ location }) => { if (`${location.pathname}${location.search}` === destination && (location.state?.authReturn || location.state?.from === GAME_PATH)) arrivals.add(location.key) })
  await beginGoogle(); await at(router, destination)
  await waitFor(() => expect(arrivals.size).toBe(1))
  expect(state === 'complete' ? router.state.location.search : router.state.location.state.from).toBe(state === 'complete' ? '?intent=join' : GAME_PATH)
})
it('F05-7: a late availability result cannot begin signup after an account switch', async () => {
  const request = deferred(); const original = http.getMockImplementation()
  http.mockImplementation((path, options) => path.startsWith('/auth/email-availability?') ? request.promise : original(path, options))
  const router = renderSignup(); await beginEmail(); server.account = account({ email: 'other@example.test' }); await emit(firebaseUser('synthetic-other'))
  await at(router, '/games'); await settle(request, { email: EMAIL, available: true })
  expect(router.state.location.pathname).toBe('/games'); expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Empty')
  expect(screen.getByLabelText('Current account')).toHaveTextContent('other@example.test')
})
it.each(['https://example.test/private', '//example.test/private', '/not-a-page'].flatMap((from) => ['google', 'restored'].map((stage) => [from, stage])))('F05-2, F05-9: an invalid saved destination uses discovery (%s, %s)', async (from, stage) => {
  server.account = account(); const router = renderSignup({ from, initialUser: stage === 'restored' ? firebaseUser() : null })
  if (stage === 'google') await beginGoogle()
  await at(router, '/games')
})
it.each(['google', 'restored'])('F05-2, F05-9: a lost saved destination uses discovery (%s)', async (stage) => {
  server.account = account(); server.returnError = error('Game not found.', 404)
  const router = renderSignup({ from: GAME_PATH, initialUser: stage === 'restored' ? firebaseUser() : null })
  if (stage === 'google') await beginGoogle()
  await at(router, '/games')
})

it.each(['success', 'failure'])('F05-7: an account switch releases the pending email check (%s)', async (outcome) => {
  const request = deferred(); const original = http.getMockImplementation()
  http.mockImplementation((path, options) => path.startsWith('/auth/email-availability?') ? request.promise : original(path, options))
  const router = renderSignup(); await beginEmail()
  await emit(firebaseUser('synthetic-f05-incomplete'))
  // Entry cleanup must be able to finish without waiting for the old email check.
  await ready()
  expect(count('/auth/unfinished-account', 'DELETE')).toBe(1)
  if (outcome === 'success') await settle(request, { email: EMAIL, available: true })
  else await settle(request, error('Could not check email availability. Please try again.'), true)
  expect(router.state.location.pathname).toBe('/create-account')
  expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Empty')
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Create Account' })).toBeEnabled()
  expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeEnabled()
})
