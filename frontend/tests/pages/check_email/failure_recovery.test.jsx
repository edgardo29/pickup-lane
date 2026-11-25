import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderCheckEmail, requestResetEmail, resend } from './checkEmailTestKit.jsx'

describe('Check Email resend recovery', () => {
  it('F09-6: a network failure shows a recoverable error', async () => {
    const user = userEvent.setup()
    vi.mocked(requestResetEmail).mockRejectedValueOnce({ code: 'auth/network-request-failed' })
    renderCheckEmail()

    await resend(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Network issue. Check your connection and try again.',
    )
  })

  it('F09-6: another Firebase failure shows a recoverable error', async () => {
    const user = userEvent.setup()
    vi.mocked(requestResetEmail).mockRejectedValueOnce({ code: 'auth/internal-error' })
    renderCheckEmail()

    await resend(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong. Please try again.')
  })

  it.each([false, true])(
    'F09-6: a network failure shows no false success (earlier success: %s)', async (earlierSuccess) => {
      const user = userEvent.setup()
      renderCheckEmail()
      if (earlierSuccess) {
        await resend(user)
        await screen.findByText('Reset email sent again.')
      }
      vi.mocked(requestResetEmail).mockRejectedValueOnce({ code: 'auth/network-request-failed' })

      await resend(user)

      await screen.findByRole('alert')
      expect(screen.queryByText('Reset email sent again.')).not.toBeInTheDocument()
    },
  )

  it.each([false, true])(
    'F09-6: another Firebase failure shows no false success (earlier success: %s)', async (earlierSuccess) => {
      const user = userEvent.setup()
      renderCheckEmail()
      if (earlierSuccess) {
        await resend(user)
        await screen.findByText('Reset email sent again.')
      }
      vi.mocked(requestResetEmail).mockRejectedValueOnce({ code: 'auth/internal-error' })

      await resend(user)

      await screen.findByRole('alert')
      expect(screen.queryByText('Reset email sent again.')).not.toBeInTheDocument()
    },
  )

  it.each(['auth/network-request-failed', 'auth/internal-error'])(
    'F09-6: a failed resend can be retried with the retained email (%s)', async (code) => {
      const user = userEvent.setup()
      vi.mocked(requestResetEmail).mockRejectedValueOnce({ code })
      renderCheckEmail('visitor@example.com')
      await resend(user)
      await screen.findByRole('alert')
      expect(screen.getByRole('button', { name: /Resend email/ })).toBeEnabled()

      await resend(user)

      expect(await screen.findByText('Reset email sent again.')).toBeVisible()
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
      expect(requestResetEmail).toHaveBeenCalledTimes(2)
      expect(requestResetEmail).toHaveBeenLastCalledWith(
        expect.any(Object), 'visitor@example.com', expect.any(Object),
      )
    },
  )
})
