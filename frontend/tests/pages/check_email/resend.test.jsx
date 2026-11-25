import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import {
  firebaseAuth,
  renderCheckEmail,
  requestResetEmail,
  resend,
  updatePassword,
} from './checkEmailTestKit.jsx'

describe('Check Email resend', () => {
  it('F09-2: resend requests another link from Firebase using the retained email', async () => {
    const user = userEvent.setup()
    renderCheckEmail('visitor@example.com')

    await resend(user)

    expect(requestResetEmail).toHaveBeenCalledExactlyOnceWith(
      firebaseAuth, 'visitor@example.com', expect.any(Object),
    )
  })

  it('F09-2: resend keeps the Reset Password link-handling route', async () => {
    const user = userEvent.setup()
    renderCheckEmail()

    await resend(user)

    expect(requestResetEmail).toHaveBeenCalledExactlyOnceWith(
      firebaseAuth, expect.any(String), {
        url: `${window.location.origin}/reset-password`,
        handleCodeInApp: true,
      },
    )
  })

  it('F09-2: successful resend displays an announced success message', async () => {
    const user = userEvent.setup()
    renderCheckEmail()
    const announcement = screen.queryByRole('status')

    await resend(user)

    expect(await screen.findByText('Reset email sent again.')).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('Reset email sent again.')
    expect(screen.getByRole('status')).toBe(announcement)
  })

  it.each(['success', 'unknown email', 'failure'])(
    'F09-2: resend stays disabled until the request settles (%s)', async (outcome) => {
      const user = userEvent.setup()
      let resolveRequest
      let rejectRequest
      vi.mocked(requestResetEmail).mockReturnValueOnce(new Promise((resolve, reject) => {
        resolveRequest = resolve
        rejectRequest = reject
      }))
      renderCheckEmail()

      await resend(user)

      const sending = screen.getByRole('button', { name: /Sending/ })
      expect(sending).toBeDisabled()
      await user.click(sending)
      expect(requestResetEmail).toHaveBeenCalledOnce()
      await act(async () => {
        if (outcome === 'success') resolveRequest()
        else rejectRequest({
          code: outcome === 'unknown email' ? 'auth/user-not-found' : 'auth/network-request-failed',
        })
      })
      expect(screen.getByRole('button', { name: /Resend email/ })).toBeEnabled()
    },
  )

  it('F09-4: no retained email disables resend and makes no Firebase request', async () => {
    const user = userEvent.setup()
    renderCheckEmail(null)

    const button = screen.getByRole('button', { name: /Resend email/ })
    expect(button).toBeDisabled()
    await user.click(button)
    expect(requestResetEmail).not.toHaveBeenCalled()
  })

  it('F09-5: unknown-email resend shows the same success without revealing account existence', async () => {
    const user = userEvent.setup()
    renderCheckEmail('unknown@example.com')
    await resend(user)
    const successText = (await screen.findByRole('status')).textContent
    vi.mocked(requestResetEmail).mockRejectedValueOnce({ code: 'auth/user-not-found' })

    await resend(user)

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(successText))
    expect(successText).toBe('Reset email sent again.')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(requestResetEmail).toHaveBeenCalledTimes(2)
  })

  it.each(['success', 'unknown email'])(
    'F09-2: resending a link does not update a password (%s)', async (outcome) => {
      const user = userEvent.setup()
      if (outcome === 'unknown email') {
        vi.mocked(requestResetEmail).mockRejectedValueOnce({ code: 'auth/user-not-found' })
      }
      renderCheckEmail()

      await resend(user)

      expect(await screen.findByText('Reset email sent again.')).toBeVisible()
      expect(updatePassword).not.toHaveBeenCalled()
    },
  )
})
