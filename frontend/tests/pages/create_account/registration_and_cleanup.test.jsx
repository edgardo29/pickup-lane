import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { at, beginEmail, beginGoogle, count, error, firebaseAuth, firebaseUser, GAME_PATH, ready, renderSignup, sdkCreate, sdkGoogle, sdkSignOut, server, submitProfile, unfinished } from './createAccountTestKit.jsx'

it.each([
  ['2026-06-16T04:59:59Z', '2008-06-16'],
  ['2026-03-01T05:59:59Z', '2008-02-29'],
  ['2026-06-15T17:00:00Z', '2026-12-01'],
])('F05-1, F05-10: ineligible profile details cannot create an email identity (%s, %s)', async (moment, birthday) => {
  vi.setSystemTime(new Date(moment)); server.profileError = error('You must be at least 18 years old to use Pickup Lane.', 422)
  const router = renderSignup(); await beginEmail(); await submitProfile(birthday)
  const alert = await screen.findByRole('alert')
  expect(sdkCreate).not.toHaveBeenCalled(); expect(alert).toHaveTextContent(/at least 18|future/)
  expect(router.state.location.pathname).toBe('/finish-profile')
  expect(count('/auth/sync-user', 'POST')).toBe(0); expect(count('/users/me', 'PATCH')).toBe(0)
})
it.each([
  ['2026-06-16T05:00:00Z', '2008-06-16'],
  ['2026-03-01T06:00:00Z', '2008-02-29'],
].flatMap(([moment, birthday]) => ['email', 'google'].map((method) => [moment, birthday, method])))('F05-10: an eligible birthday completes signup (%s, %s, %s)', async (moment, birthday, method) => {
  vi.setSystemTime(new Date(moment)); const router = renderSignup({ from: GAME_PATH })
  if (method === 'email') await beginEmail(); else await beginGoogle()
  await submitProfile(birthday); await at(router, GAME_PATH)
  expect(sdkCreate).toHaveBeenCalledTimes(method === 'email' ? 1 : 0); expect(sdkGoogle).toHaveBeenCalledTimes(method === 'google' ? 1 : 0); expect(count('/auth/sync-user', 'POST')).toBe(1); expect(count('/users/me', 'PATCH')).toBe(1)
  expect(server.account.date_of_birth).toBe(birthday)
})
const cleanupEntries = [['back', null], ['back', unfinished()], ['entry', null]]
it.each(cleanupEntries)('F05-3: abandoning Google signup cleans up before returning (%s, %j)', async (stage, existing) => {
  server.account = existing
  const router = renderSignup({ initialUser: stage === 'entry' ? firebaseUser() : null })
  if (stage === 'back') {
    await beginGoogle(); await at(router, '/finish-profile')
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Back to create account' }))
  }
  await at(router, '/create-account'); await ready()
  expect(count('/auth/unfinished-account', 'DELETE')).toBe(1); expect(sdkSignOut).toHaveBeenCalledTimes(1)
  expect(firebaseAuth.currentUser).toBeNull(); expect(server.account).toBeNull()
})
it.each(cleanupEntries)('F05-7: failed Google cleanup preserves recovery and can be retried (%s, %j)', async (stage, existing) => {
  server.account = existing; server.cleanupError = error('Firebase could not clean up this sign-up. Please try again.', 502)
  const router = renderSignup({ initialUser: stage === 'entry' ? firebaseUser() : null })
  if (stage === 'back') {
    await beginGoogle(); await at(router, '/finish-profile')
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Back to create account' }))
  }
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not cancel sign-up. Please try again.')
  expect(router.state.location.pathname).toBe(stage === 'back' ? '/finish-profile' : '/create-account')
  expect(firebaseAuth.currentUser?.uid).toBe('synthetic-f05-user'); expect(sdkSignOut).not.toHaveBeenCalled()
  server.cleanupError = null
  await userEvent.setup().click(screen.getByRole('button', { name: stage === 'back' ? 'Back to create account' : 'Retry signup cleanup' }))
  await at(router, '/create-account'); await ready()
  expect(count('/auth/unfinished-account', 'DELETE')).toBe(2)
})
