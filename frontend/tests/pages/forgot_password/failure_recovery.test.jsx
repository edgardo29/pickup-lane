import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  renderForgotPassword,
  requestResetEmail as sendPasswordResetEmail,
  submitReset,
} from './forgotPasswordTestKit.jsx'

const failures = [
  ['network', 'auth/network-request-failed', 'Network issue. Check your connection and try again.'],
  ['Firebase', 'auth/internal-error', 'Something went wrong. Please try again.'],
]

describe('Forgot Password failure recovery', () => {
  it.each(failures)('F08-5: a %s failure shows recoverable feedback on Forgot Password', async (_case, code, message) => {
    const user = userEvent.setup()
    vi.mocked(sendPasswordResetEmail).mockRejectedValueOnce({ code })
    const router = renderForgotPassword()

    await submitReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(router.state.location.pathname).toBe('/forgot-password')
  })

  it.each(failures)('F08-5: a %s failure never claims reset-email success', async (_case, code) => {
    const user = userEvent.setup()
    vi.mocked(sendPasswordResetEmail).mockRejectedValueOnce({ code })
    const router = renderForgotPassword()

    await submitReset(user)

    expect(screen.queryByRole('heading', { name: 'Check your email' })).not.toBeInTheDocument()
    expect(screen.queryByText(/If an account exists, we sent/)).not.toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/forgot-password')
  })

  it.each(failures)('F08-5: after a %s failure the retained email can be retried successfully', async (_case, code) => {
    const user = userEvent.setup()
    vi.mocked(sendPasswordResetEmail).mockRejectedValueOnce({ code })
    renderForgotPassword()

    await submitReset(user)
    await screen.findByRole('alert')
    expect(screen.getByRole('button', { name: /Send Reset Link|Sending/ })).toBeEnabled()
    expect(screen.getByRole('textbox', { name: 'Email' })).toHaveValue('player@example.com')
    await user.click(screen.getByRole('button', { name: 'Send Reset Link' }))

    expect(sendPasswordResetEmail).toHaveBeenCalledTimes(2)
    expect(sendPasswordResetEmail).toHaveBeenLastCalledWith(
      expect.anything(), 'player@example.com', expect.any(Object),
    )
    expect(await screen.findByRole('heading', { name: 'Check your email' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('Forgot Password service-error accessibility', () => {
  it.each(failures)('F08-5: a %s failure does not mark the valid email invalid', async (_case, code, message) => {
    const user = userEvent.setup()
    vi.mocked(sendPasswordResetEmail).mockRejectedValueOnce({ code })
    renderForgotPassword()

    await submitReset(user)
    expect(await screen.findByRole('alert')).toHaveTextContent(message)

    const emailInput = screen.getByRole('textbox', { name: 'Email' })
    expect(emailInput).toHaveAttribute('aria-invalid', 'false')
    expect(emailInput).not.toHaveAttribute('aria-describedby')
  })
})
