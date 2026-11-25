import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  confirmReset, deferred, firebaseAuth, firebaseError, passwordInput,
  renderResetPassword, renderResetWithAuthUpdates, checkResetCode, saveErrors, savePassword, settle,
} from './resetPasswordTestKit.jsx'

it.each(['Newpass1', 'Newpass!', 'Newpass_'])('F10-2: a valid minimum-length password and checked code are sent to Firebase (%s)', async (password) => {
  const user = userEvent.setup()
  renderResetPassword()
  await savePassword(user, password)
  expect(confirmReset).toHaveBeenCalledExactlyOnceWith(firebaseAuth, 'current-code', password)
})

it('F10-2: Firebase acceptance announces that the password changed', async () => {
  const user = userEvent.setup()
  renderResetPassword()
  const status = screen.queryByRole('status')
  await savePassword(user)
  expect(screen.getByRole('status')).toBe(status)
  expect(within(status).getByRole('heading', { name: 'Password changed' })).toBeVisible()
  expect(status).toHaveTextContent('You can now sign in with your new password.')
})

it('F10-2: a successful save replaces the password form', async () => {
  renderResetPassword()
  await savePassword(userEvent.setup())
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Save Password' })).not.toBeInTheDocument()
})

it('F10-2: Sign In from the success confirmation opens Sign In', async () => {
  const user = userEvent.setup()
  const router = renderResetPassword()
  await savePassword(user)
  await user.click(screen.getByRole('link', { name: 'Back to Sign In' }))
  expect(router.state.location.pathname).toBe('/sign-in')
  expect(screen.getByRole('heading', { name: 'Sign In' })).toBeVisible()
})

it.each(saveErrors)('F10-6: a failed save reports a recoverable error (%s)', async (code, message) => {
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  renderResetPassword()
  await savePassword(userEvent.setup())
  expect(screen.getByRole('alert')).toHaveTextContent(message)
  expect(passwordInput()).toHaveValue('Newpass1')
  expect(screen.getByRole('button', { name: 'Save Password' })).toBeEnabled()
})

it.each(saveErrors)('F10-6: a rejected save never claims the password changed (%s)', async (code) => {
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  renderResetPassword()
  await savePassword(userEvent.setup())
  expect(confirmReset).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('heading', { name: 'Password changed' })).not.toBeInTheDocument()
})

it.each(saveErrors)('F10-6: a recoverable failure allows a successful retry (%s)', async (code) => {
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  const user = userEvent.setup()
  renderResetPassword()
  await savePassword(user)
  await user.click(screen.getByRole('button', { name: 'Save Password' }))
  expect(confirmReset).toHaveBeenNthCalledWith(2, firebaseAuth, 'current-code', 'Newpass1')
  expect(screen.getByRole('heading', { name: 'Password changed' })).toBeVisible()
})

it.each(['resolve', 'reject'])('F10-8: saving stays disabled until Firebase settles (%s)', async (outcome) => {
  const request = deferred()
  vi.mocked(confirmReset).mockReturnValueOnce(request.promise)
  const user = userEvent.setup()
  renderResetPassword()
  await savePassword(user)
  const save = screen.getByRole('button', { name: 'Saving...' })
  expect(save).toBeDisabled()
  await user.click(save)
  expect(confirmReset).toHaveBeenCalledTimes(1)
  await settle(request, outcome === 'reject' ? firebaseError('auth/network-request-failed') : undefined, outcome === 'reject')
  if (outcome === 'reject') expect(screen.getByRole('button', { name: 'Save Password' })).toBeEnabled()
  else expect(screen.getByRole('heading', { name: 'Password changed' })).toBeVisible()
})

it('F10-2: the password is sent only to Firebase, never the app API or browser storage', async () => {
  const stored = vi.spyOn(Storage.prototype, 'setItem')
  renderResetPassword()
  await savePassword(userEvent.setup(), 'Private1!')
  expect(confirmReset).toHaveBeenCalledExactlyOnceWith(firebaseAuth, 'current-code', 'Private1!')
  expect(fetch).not.toHaveBeenCalled()
  expect(stored).not.toHaveBeenCalled()
})

it.each(['resolve', 'reject'])('F10-8: authentication updates keep saving disabled until its request settles (%s)', async (outcome) => {
  const request = deferred()
  vi.mocked(confirmReset).mockReturnValueOnce(request.promise)
  const user = userEvent.setup()
  const updateAuthentication = renderResetWithAuthUpdates()
  await savePassword(user)
  await updateAuthentication()
  const save = screen.getByRole('button', { name: /Save Password|Saving\.\.\./ })
  expect(save).toBeDisabled()
  expect(checkResetCode).toHaveBeenCalledTimes(1)
  await user.click(save)
  expect(confirmReset).toHaveBeenCalledTimes(1)
  await settle(request, outcome === 'reject' ? firebaseError('auth/network-request-failed') : undefined, outcome === 'reject')
  if (outcome === 'reject') expect(screen.getByRole('button', { name: 'Save Password' })).toBeEnabled()
  else expect(screen.getByRole('heading', { name: 'Password changed' })).toBeVisible()
})

it('F10-2: authentication updates preserve the successful password-change confirmation', async () => {
  const updateAuthentication = renderResetWithAuthUpdates()
  await savePassword(userEvent.setup())
  expect(screen.getByRole('heading', { name: 'Password changed' })).toBeVisible()
  // Firebase has consumed the code; an unnecessary recheck would now reject it.
  vi.mocked(checkResetCode).mockRejectedValueOnce(firebaseError('auth/invalid-action-code'))
  await updateAuthentication()
  expect(screen.getByRole('heading', { name: 'Password changed' })).toBeVisible()
  expect(checkResetCode).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})
