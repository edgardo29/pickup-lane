import { act, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  apiRequestMock, applyCode, firebaseAuth, controlTimers, deferred, finishUnconfirmed,
  firebaseError, firebaseUser, origins, renderVerification, verificationUrl, VERIFIED_AT,
} from './emailVerificationTestKit.jsx'

it('F11-1: a pending verification shows checking feedback', () => {
  vi.mocked(applyCode).mockReturnValue(deferred().promise)
  renderVerification()
  expect(screen.getByRole('heading', { name: 'Verifying email' })).toBeVisible()
})
it('F11-1: the verification route sends its code to Firebase', () => {
  vi.mocked(applyCode).mockReturnValue(deferred().promise)
  renderVerification({ path: verificationUrl('/create-game', 'specific-link-code') })
  expect(applyCode).toHaveBeenCalledExactlyOnceWith(firebaseAuth, 'specific-link-code')
})
it('F11-1: verification reloads Firebase and updates the current app account', async () => {
  const view = renderVerification()
  await screen.findByRole('heading', { name: 'Email verified' })
  expect(view.getAppUser().email_verified_at).toBe(VERIFIED_AT)
  expect(firebaseUser.reload).toHaveBeenCalled()
  expect(firebaseUser.getIdToken).toHaveBeenCalledWith(true)
  expect(apiRequestMock).toHaveBeenCalledWith('/auth/sync-user', expect.objectContaining({
    method: 'POST', headers: { Authorization: 'Bearer synthetic-id-token' },
  }))
})
it('F11-1: confirmed current account verification shows success', async () => {
  renderVerification()
  expect(await screen.findByRole('heading', { name: 'Email verified' })).toBeVisible()
})
it('F11-1: a verified signed-in account continues without authentication', async () => {
  const user = userEvent.setup()
  const { router } = renderVerification()
  await user.click(await screen.findByRole('link', { name: 'Continue' }))
  expect(router.state.location.pathname).not.toBe('/sign-in')
  expect(await screen.findByLabelText('Start time')).toBeVisible()
})
const badLinks = [['missing', '', null], ['invalid', 'bad-code', 'auth/invalid-action-code'], ['expired', 'expired-code', 'auth/expired-action-code'], ['used', 'used-code', 'auth/invalid-action-code']]
it.each(badLinks)('F11-3: an unusable link explains the failure (%s)', async (_label, code, errorCode) => {
  controlTimers()
  if (errorCode) vi.mocked(applyCode).mockRejectedValue(firebaseError(errorCode))
  renderVerification({ path: verificationUrl('/create-game', code) })
  await finishUnconfirmed()
  expect(screen.getByRole('alert')).toHaveTextContent(code ? /expired or already used/i : /missing or invalid/i)
})
it.each(badLinks)('F11-3: an unusable unverified account never claims success (%s)', async (_label, code, errorCode) => {
  controlTimers()
  if (errorCode) vi.mocked(applyCode).mockRejectedValue(firebaseError(errorCode))
  renderVerification({ path: verificationUrl('/create-game', code) })
  await finishUnconfirmed()
  expect(screen.queryByRole('heading', { name: 'Email verified' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Continue' })).not.toBeInTheDocument()
})
it.each(origins)('F11-3: an unavailable link offers a fresh email at its origin (%s)', async (destination) => {
  renderVerification({ path: verificationUrl(destination, '') })
  const label = destination.startsWith('/need-a-sub') ? 'Create Sub Post' : 'Create Game'
  expect(screen.getByRole('link', { name: `Back to ${label}` })).toHaveAttribute('href', `${destination}${destination.includes('?') ? '&' : '?'}verification=return`)
})
it('F11-4: refreshed verification permits success for a reused code', async () => {
  vi.mocked(applyCode).mockRejectedValue(firebaseError('auth/invalid-action-code'))
  renderVerification({ verified: true })
  expect(await screen.findByRole('heading', { name: 'Email verified' })).toBeVisible()
  expect(firebaseUser.reload).toHaveBeenCalled()
})
it.each(['unverified', 'signed-out', 'refresh-failed'])('F11-5: an applied but unconfirmed link has a distinct outcome (%s)', async (reason) => {
  controlTimers()
  vi.mocked(applyCode).mockResolvedValue(undefined)
  if (reason === 'refresh-failed') firebaseUser.reload.mockRejectedValue(new Error('Network unavailable'))
  renderVerification({ signedIn: reason !== 'signed-out' })
  // No signed-in Firebase user resolves directly, without waiting for an auth event.
  if (reason === 'signed-out') await act(async () => vi.advanceTimersByTimeAsync(18000))
  else await finishUnconfirmed()
  expect(screen.getByRole('heading', { name: 'Verification not confirmed' })).toBeVisible()
})
it('F11-5: unconfirmed account state never claims hosting access', async () => {
  controlTimers()
  vi.mocked(applyCode).mockResolvedValue(undefined)
  renderVerification()
  await finishUnconfirmed()
  expect(screen.queryByRole('heading', { name: 'Email verified' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'Continue' })).not.toBeInTheDocument()
  expect(screen.queryByText(/you can now publish/i)).not.toBeInTheDocument()
})
it.each(origins)('F11-5: unconfirmed verification offers a fresh email at its origin (%s)', async (destination) => {
  controlTimers()
  vi.mocked(applyCode).mockResolvedValue(undefined)
  renderVerification({ path: verificationUrl(destination) })
  await finishUnconfirmed()
  const label = destination.startsWith('/need-a-sub') ? 'Create Sub Post' : 'Create Game'
  expect(screen.getByRole('link', { name: `Back to ${label}` })).toHaveAttribute('href', `${destination}${destination.includes('?') ? '&' : '?'}verification=return`)
})
it.each(['checking', 'success', 'invalid', 'unconfirmed'])('F11-1, F11-3, F11-5: verification feedback is announced (%s)', async (outcome) => {
  controlTimers()
  if (outcome === 'checking') vi.mocked(applyCode).mockReturnValue(deferred().promise)
  if (outcome === 'unconfirmed') vi.mocked(applyCode).mockResolvedValue(undefined)
  renderVerification({ path: verificationUrl('/create-game', outcome === 'invalid' ? '' : 'code') })
  if (outcome !== 'checking') await finishUnconfirmed()
  const expected = { checking: 'Verifying email', success: 'Email verified', invalid: 'Verification link unavailable', unconfirmed: 'Verification not confirmed' }
  expect(within(screen.getByRole('status')).getByRole('heading', { name: expected[outcome] })).toBeVisible()
})
