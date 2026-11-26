import { screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import {
  applyCode, deferred, firebaseUser, navigate,
  renderVerification, server, settle, verificationUrl,
} from './emailVerificationTestKit.jsx'

it.each(['success', 'pending'])('F11-1: a new link ignores replies from the preceding link (%s)', async (previous) => {
  const old = deferred(), next = deferred()
  vi.mocked(applyCode).mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise)
  const view = renderVerification()
  if (previous === 'success') { server.verified = true; await settle(old) }
  await navigate(view.router, verificationUrl('/create-game', 'next-code'))
  expect(screen.getByRole('heading', { name: 'Verifying email' })).toBeVisible()
  server.verified = true
  await settle(next)
  expect(await screen.findByRole('heading', { name: 'Email verified' })).toBeVisible()
  if (previous === 'pending') await settle(old)
  expect(screen.getByRole('heading', { name: 'Email verified' })).toBeVisible()
  expect(applyCode).toHaveBeenLastCalledWith(expect.anything(), 'next-code')
})
it.each(['success', 'pending'])('F11-3: removing the code replaces the preceding link result (%s)', async (previous) => {
  const old = deferred()
  vi.mocked(applyCode).mockReturnValue(old.promise)
  const view = renderVerification()
  if (previous === 'success') { server.verified = true; await settle(old) }
  await navigate(view.router, verificationUrl('/create-game', ''))
  await settle(old)
  expect(screen.getByRole('heading', { name: 'Verification link unavailable' })).toBeVisible()
  expect(screen.queryByRole('link', { name: 'Continue' })).not.toBeInTheDocument()
})
it.each(['pending', 'success'])('F11-1, F11-7: authentication updates preserve the same verification operation (%s)', async (stage) => {
  const action = deferred()
  vi.mocked(applyCode).mockReturnValue(action.promise)
  const view = renderVerification()
  if (stage === 'success') { server.verified = true; await settle(action) }
  await view.updateAuthentication(true)
  await view.updateAuthentication(false)
  expect(applyCode).toHaveBeenCalledTimes(1)
  if (stage === 'pending') {
    expect(screen.getByRole('heading', { name: 'Verifying email' })).toBeVisible()
    server.verified = true
    await settle(action)
  }
  expect(await screen.findByRole('heading', { name: 'Email verified' })).toBeVisible()
})

it('F11-1: restoring sign-in applies the verification code once', async () => {
  const action = deferred()
  vi.mocked(applyCode).mockReturnValue(action.promise)
  const view = renderVerification({ signedIn: false, loading: true })
  expect(screen.getByRole('heading', { name: 'Verifying email' })).toBeVisible()
  expect(applyCode).not.toHaveBeenCalled()
  await view.setSession(firebaseUser, true)
  expect(applyCode).not.toHaveBeenCalled()
  await view.updateAuthentication(false)
  expect(applyCode).toHaveBeenCalledTimes(1)
  server.verified = true
  await settle(action)
  expect(await screen.findByRole('heading', { name: 'Email verified' })).toBeVisible()
  expect(applyCode).toHaveBeenCalledTimes(1)
})
