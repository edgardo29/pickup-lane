import { act, renderHook, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { usePasswordResetForm } from '../../../src/pages/auth/usePasswordResetForm.js'
import {
  buildCredentialActions, confirmReset, firebaseError, renderResetPassword,
  savePassword, unavailableLinks, unusableSaveCodes, fallbackUpdate,
} from './resetPasswordTestKit.jsx'

it.each(unusableSaveCodes)('F10-9: an expired or used code clears the entered replacement password (%s)', async (code) => {
  const actions = buildCredentialActions({})
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  const { result } = renderHook(() => usePasswordResetForm({ code: 'current-code', mode: 'resetPassword', ...actions }))
  await waitFor(() => expect(result.current.status).toBe('ready'))
  act(() => result.current.setPassword('Private1!'))
  await act(async () => { await result.current.handleResetPassword({ preventDefault() {} }) })
  expect(result.current.password).toBe('')
})

it.each(unusableSaveCodes)('F10-9: a code rejected during saving explains the link problem (%s)', async (code) => {
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  renderResetPassword()
  await savePassword(userEvent.setup())
  const message = unavailableLinks.find((link) => link[2] === code)[3]
  expect(screen.getByRole('alert')).toHaveTextContent(message)
})

it.each(unusableSaveCodes)('F10-9: Request New Reset Link opens the request flow after a rejected save (%s)', async (code) => {
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  const user = userEvent.setup()
  const router = renderResetPassword()
  await savePassword(user)
  await user.click(screen.getByRole('link', { name: 'Request New Reset Link' }))
  expect(router.state.location.pathname).toBe('/forgot-password')
  expect(screen.getByRole('textbox', { name: 'Email' })).toBeVisible()
  expect(screen.getByRole('button', { name: 'Send Reset Link' })).toBeEnabled()
})

it.each(unusableSaveCodes)('F10-9: a rejected unusable code never claims success or tries a fallback password update (%s)', async (code) => {
  vi.mocked(confirmReset).mockRejectedValueOnce(firebaseError(code))
  renderResetPassword()
  await savePassword(userEvent.setup())
  expect(confirmReset).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('heading', { name: 'Password changed' })).not.toBeInTheDocument()
  expect(fallbackUpdate).not.toHaveBeenCalled()
  expect(fetch).not.toHaveBeenCalled()
})
