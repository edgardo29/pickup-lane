import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  deferred, firebaseAuth, firebaseError, readyPasswordForm, renderResetPassword,
  renderUnavailableLink, settle, unavailableLinks, checkResetCode,
} from './resetPasswordTestKit.jsx'

it.each(['', '&mode=resetPassword'])('F10-1: Firebase checks the URL code before the form opens (%s)', async (mode) => {
  const request = deferred()
  vi.mocked(checkResetCode).mockReturnValueOnce(request.promise)
  renderResetPassword(`/reset-password?oobCode=url-code${mode}`)
  expect(checkResetCode).toHaveBeenCalledExactlyOnceWith(firebaseAuth, 'url-code')
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
  await settle(request, 'player@example.com')
  await readyPasswordForm()
})

it('F10-1: a pending check announces progress without exposing the form', () => {
  vi.mocked(checkResetCode).mockReturnValueOnce(deferred().promise)
  renderResetPassword()
  expect(within(screen.getByRole('status')).getByRole('heading', { name: 'Checking reset link' })).toBeVisible()
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
})

it('F10-1: a verified reset code opens the password form', async () => {
  renderResetPassword()
  expect(await readyPasswordForm()).toBeVisible()
})

it('F10-1: the form shows the email returned by Firebase', async () => {
  vi.mocked(checkResetCode).mockResolvedValueOnce('another@example.com')
  renderResetPassword()
  await readyPasswordForm()
  expect(screen.getByText('another@example.com')).toBeVisible()
})

it('F10-1: a valid check without an email still opens the form', async () => {
  vi.mocked(checkResetCode).mockResolvedValueOnce('')
  renderResetPassword()
  expect(await readyPasswordForm()).toBeVisible()
  expect(screen.getByText('Create a new password for your account.')).toBeVisible()
})

it.each(unavailableLinks)('F10-4: an unavailable link never exposes the form (%s)', async (_kind, code, errorCode) => {
  renderUnavailableLink(code, errorCode)
  await screen.findByRole('alert')
  expect(screen.queryByLabelText(/^New password/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Save Password' })).not.toBeInTheDocument()
})

it.each(unavailableLinks)('F10-4: the link problem is explained (%s)', async (_kind, code, errorCode, message) => {
  renderUnavailableLink(code, errorCode)
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
})

it.each(unavailableLinks)('F10-4: Request New Reset Link opens Forgot Password (%s)', async (_kind, code, errorCode) => {
  const user = userEvent.setup()
  const router = renderUnavailableLink(code, errorCode)
  await user.click(await screen.findByRole('link', { name: 'Request New Reset Link' }))
  expect(router.state.location.pathname).toBe('/forgot-password')
  expect(screen.getByRole('textbox', { name: 'Email' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Send Reset Link' })).toBeEnabled()
})

it.each([
  ['auth/network-request-failed', /Network issue/],
  ['auth/internal-error', /Something went wrong/],
])('F10-4: a failed link check offers recovery without falsely calling the link expired (%s)', async (code, message) => {
  vi.mocked(checkResetCode).mockRejectedValueOnce(firebaseError(code))
  renderResetPassword()
  expect(await screen.findByRole('alert')).toHaveTextContent(message)
  expect(screen.queryByRole('heading', { name: /expired|already used/i })).not.toBeInTheDocument()
  expect(screen.queryByText(/link is invalid or has already been used/i)).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Request New Reset Link' })).toBeVisible()
})
