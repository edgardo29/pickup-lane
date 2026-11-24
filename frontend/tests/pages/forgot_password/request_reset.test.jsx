import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  firebaseAuth as auth,
  renderForgotPassword,
  requestResetEmail as sendPasswordResetEmail,
  submitReset,
} from './forgotPasswordTestKit.jsx'

describe('Forgot Password reset request', () => {
  it('F08-1: submitting a valid email requests a reset through Firebase', async () => {
    const user = userEvent.setup()
    renderForgotPassword()

    await submitReset(user, '  Player@Example.COM  ')

    expect(sendPasswordResetEmail).toHaveBeenCalledOnce()
    expect(sendPasswordResetEmail).toHaveBeenCalledWith(
      auth, 'Player@Example.COM', expect.any(Object),
    )
  })

  it('F08-1: an accepted request opens Check Email with normalized email', async () => {
    const user = userEvent.setup()
    const router = renderForgotPassword()

    await submitReset(user, '  Player@Example.COM  ')

    await waitFor(() => expect(router.state.location).toMatchObject({
      pathname: '/check-email', state: { email: 'player@example.com' },
    }))
  })

  it('F08-1: an accepted request shows the non-disclosing confirmation', async () => {
    const user = userEvent.setup()
    renderForgotPassword()

    await submitReset(user)

    expect(await screen.findByText(/If an account exists, we sent/)).toHaveTextContent(
      'If an account exists, we sent a password reset link to player@example.com.',
    )
  })

  it('F08-2: an unknown account follows the same non-disclosing confirmation route', async () => {
    const user = userEvent.setup()
    vi.mocked(sendPasswordResetEmail).mockRejectedValueOnce({ code: 'auth/user-not-found' })
    const router = renderForgotPassword()

    await submitReset(user, 'unknown@example.com')

    expect(await screen.findByText(/If an account exists, we sent/)).toHaveTextContent(
      'If an account exists, we sent a password reset link to unknown@example.com.',
    )
    expect(router.state.location.pathname).toBe('/check-email')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('F08-6: a pending request disables duplicate submission until it settles', async () => {
    const user = userEvent.setup()
    let finishRequest
    const request = new Promise((resolve) => { finishRequest = resolve })
    vi.mocked(sendPasswordResetEmail).mockReturnValueOnce(request)
    renderForgotPassword()

    await submitReset(user)

    const pendingButton = screen.getByRole('button', { name: 'Sending...' })
    expect(pendingButton).toBeDisabled()
    await user.click(pendingButton)
    expect(sendPasswordResetEmail).toHaveBeenCalledOnce()

    await act(async () => finishRequest())
    await screen.findByRole('heading', { name: 'Check your email' })
  })
})
