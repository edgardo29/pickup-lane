import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  updatePassword as confirmPasswordReset,
  renderForgotPassword,
  requestResetEmail as sendPasswordResetEmail,
  submitReset,
} from './forgotPasswordTestKit.jsx'

describe('Forgot Password credential safety', () => {
  it('F08-3: Back opens Sign In without requesting or changing a password', async () => {
    const user = userEvent.setup()
    const router = renderForgotPassword()

    await user.click(screen.getByRole('link', { name: 'Back to sign in' }))

    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/sign-in')
    expect(sendPasswordResetEmail).not.toHaveBeenCalled()
    expect(confirmPasswordReset).not.toHaveBeenCalled()
  })

  it('F08-1: requesting an email never updates the password', async () => {
    const user = userEvent.setup()
    renderForgotPassword()

    await submitReset(user)
    await screen.findByRole('heading', { name: 'Check your email' })

    expect(confirmPasswordReset).not.toHaveBeenCalled()
  })
})

// Firebase finishes the request after Back has closed Forgot Password.
describe('Forgot Password pending navigation', () => {
  it.each([
    ['succeeds', null],
    ['reports an unknown account', 'auth/user-not-found'],
  ])('F08-3: Back stays on Sign In when the pending request %s', async (_case, code) => {
    const user = userEvent.setup()
    let resolveRequest
    let rejectRequest
    const request = new Promise((resolve, reject) => {
      resolveRequest = resolve
      rejectRequest = reject
    })
    vi.mocked(sendPasswordResetEmail).mockReturnValueOnce(request)
    const router = renderForgotPassword()

    await submitReset(user)
    await user.click(screen.getByRole('link', { name: 'Back to sign in' }))
    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()

    await act(async () => {
      if (code) {
        rejectRequest({ code })
      } else {
        resolveRequest()
      }
      await request.catch(() => {})
    })

    expect(router.state.location.pathname).toBe('/sign-in')
    expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(confirmPasswordReset).not.toHaveBeenCalled()
  })
})
