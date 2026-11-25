import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  applyEmailCode, confirmReset, deferred, firebaseAuth, firebaseError,
  navigate, passwordInput, readyPasswordForm, renderResetPassword, savePassword,
  settle, checkResetCode,
} from './resetPasswordTestKit.jsx'

it.each(['recoverEmail', 'unsupported'])('F10-7: an unsupported mode redirects to Sign In without resetting (%s)', async (mode) => {
  const router = renderResetPassword(`/reset-password?mode=${mode}&oobCode=current-code`)
  expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeVisible()
  expect(router.state.location.pathname).toBe('/sign-in')
  expect(checkResetCode).not.toHaveBeenCalled()
  expect(confirmReset).not.toHaveBeenCalled()
})

it.each(['ready', 'checking-success', 'checking-failure'])('F10-1: a changed URL checks its own code and ignores earlier replies (%s)', async (previous) => {
  const oldCheck = deferred(), newCheck = deferred()
  vi.mocked(checkResetCode).mockReturnValueOnce(oldCheck.promise).mockReturnValueOnce(newCheck.promise)
  const router = renderResetPassword()
  if (previous === 'ready') {
    await settle(oldCheck, 'old@example.com')
    await readyPasswordForm()
    await userEvent.setup().type(passwordInput(), 'Oldpass1')
  }
  await navigate(router, '/reset-password?oobCode=new-code')
  expect(checkResetCode).toHaveBeenLastCalledWith(firebaseAuth, 'new-code')
  expect(screen.getByRole('heading', { name: 'Checking reset link' })).toBeVisible()
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
  await settle(newCheck, 'new@example.com')
  if (previous !== 'ready') await settle(oldCheck, previous === 'checking-failure' ? firebaseError('auth/invalid-action-code') : 'old@example.com', previous === 'checking-failure')
  expect(await readyPasswordForm()).toHaveValue('')
  expect(screen.getByText('new@example.com')).toBeVisible()
  expect(screen.queryByText('old@example.com')).not.toBeInTheDocument()
})

it.each(['ready', 'checking'])('F10-4: removing the URL code shows the missing-link result (%s)', async (previous) => {
  const check = deferred()
  vi.mocked(checkResetCode).mockReturnValueOnce(check.promise)
  const router = renderResetPassword()
  if (previous === 'ready') await settle(check, 'player@example.com')
  await navigate(router, '/reset-password')
  if (previous === 'checking') await settle(check, 'player@example.com')
  expect(screen.getByRole('alert')).toHaveTextContent('This reset link is missing or invalid.')
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Checking reset link' })).not.toBeInTheDocument()
})

it.each([
  ['checking', 'success'], ['checking', 'failure'],
  ['ready', 'success'], ['ready', 'failure'],
  ['invalid', 'success'], ['invalid', 'failure'],
])('F10-2, F10-6: an earlier save cannot replace the current link state (%s, %s)', async (current, outcome) => {
  const save = deferred(), check = deferred()
  vi.mocked(confirmReset).mockReturnValueOnce(save.promise)
  const router = renderResetPassword()
  await savePassword(userEvent.setup())
  vi.mocked(checkResetCode).mockReturnValueOnce(check.promise)
  await navigate(router, '/reset-password?oobCode=new-code')
  if (current !== 'checking') await settle(check, current === 'invalid' ? firebaseError('auth/invalid-action-code') : 'new@example.com', current === 'invalid')
  await settle(save, outcome === 'failure' ? firebaseError('auth/network-request-failed') : undefined, outcome === 'failure')
  if (current === 'checking') {
    expect(screen.getByRole('heading', { name: 'Checking reset link' })).toBeVisible()
    expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
  } else if (current === 'ready') {
    expect(screen.getByRole('heading', { name: 'Reset your password' })).toBeVisible()
    expect(passwordInput()).toHaveValue('')
    expect(screen.getByText('new@example.com')).toBeVisible()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  } else expect(screen.getByRole('alert')).toHaveTextContent(/invalid or has already been used/i)
  expect(screen.queryByRole('heading', { name: 'Password changed' })).not.toBeInTheDocument()
})

it('F10-7: email-verification mode opens email verification without a password reset', () => {
  vi.mocked(applyEmailCode).mockReturnValueOnce(deferred().promise)
  renderResetPassword('/reset-password?mode=verifyEmail&oobCode=verification-code')
  expect(screen.getByRole('heading', { name: 'Verifying email' })).toBeVisible()
  expect(applyEmailCode).toHaveBeenCalledExactlyOnceWith(firebaseAuth, 'verification-code')
  expect(checkResetCode).not.toHaveBeenCalled()
  expect(confirmReset).not.toHaveBeenCalled()
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
})
