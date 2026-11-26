import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  deferred, firebaseError, firebaseUser, renderVerification, sendVerification, settle,
} from './emailVerificationTestKit.jsx'

function otherAccount() {
  return { ...firebaseUser, uid: 'another-synthetic-account', email: 'another@example.test' }
}

it.each(['sent', 'error'])('F11-3: changing accounts clears the previous send feedback (%s)', async (outcome) => {
  const user = userEvent.setup()
  if (outcome === 'error') vi.mocked(sendVerification).mockRejectedValueOnce(firebaseError('auth/network-request-failed'))
  const view = renderVerification({ path: '/need-a-sub?panel=create' })
  await user.click(screen.getByRole('button', { name: 'Send verification email' }))
  if (outcome === 'sent') expect(screen.getByRole('button', { name: 'Try again in 60s' })).toBeDisabled()
  else expect(screen.getByRole('alert')).toHaveTextContent(/Network issue/)
  // Firebase changes account without navigating away from this public route.
  await view.setSession(null, true)
  await view.setSession(otherAccount())
  expect(screen.queryByText('Check your email to continue.')).not.toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Send verification email' })).toBeEnabled()
  // The original account keeps its own cooldown when it signs back in.
  if (outcome === 'sent') {
    await view.setSession(firebaseUser)
    expect(await screen.findByRole('button', { name: 'Try again in 60s' })).toBeDisabled()
  }
})

it.each(['success', 'failure'])('F11-3: an earlier account request cannot replace the current send (%s)', async (outcome) => {
  const user = userEvent.setup()
  const previous = deferred(), current = deferred()
  vi.mocked(sendVerification).mockReturnValueOnce(previous.promise).mockReturnValueOnce(current.promise)
  const view = renderVerification({ path: '/need-a-sub?panel=create' })
  await user.click(screen.getByRole('button', { name: 'Send verification email' }))
  await view.setSession(null, true)
  const nextUser = otherAccount()
  await view.setSession(nextUser)
  const sendButton = screen.getByRole('button', { name: 'Send verification email' })
  expect(sendButton).toBeEnabled()
  await user.click(sendButton)
  expect(sendVerification).toHaveBeenCalledTimes(2)
  expect(sendVerification).toHaveBeenLastCalledWith(nextUser, expect.anything())
  await settle(previous, outcome === 'failure' ? firebaseError('auth/network-request-failed') : undefined, outcome === 'failure')
  expect(screen.getByRole('button', { name: 'Sending...' })).toBeDisabled()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  await act(async () => current.resolve())
  expect(screen.getByRole('button', { name: 'Try again in 60s' })).toBeDisabled()
})
