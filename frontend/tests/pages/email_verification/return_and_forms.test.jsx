import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import {
  apiRequestMock, applyCode, firebaseAuth, firebaseError, firebaseUser, navigate,
  origins, renderVerification, sendVerification, server, verificationUrl,
} from './emailVerificationTestKit.jsx'

it.each(origins)('F11-1: Firebase email settings preserve the originating creation destination (%s)', async (destination) => {
  const user = userEvent.setup()
  renderVerification({ path: destination })
  await user.click(await screen.findByRole('button', { name: 'Send verification email' }))
  expect(sendVerification).toHaveBeenCalledExactlyOnceWith(firebaseUser, {
    url: `${window.location.origin}${destination}${destination.includes('?') ? '&' : '?'}verification=return`,
    handleCodeInApp: false,
  })
})
it.each(origins)('F11-3: the originating entry supports failure recovery and resend (%s)', async (destination) => {
  const user = userEvent.setup()
  vi.mocked(sendVerification).mockRejectedValueOnce(firebaseError('auth/network-request-failed'))
  renderVerification({ path: destination })
  await user.click(screen.getByRole('button', { name: 'Send verification email' }))
  expect(screen.getByRole('alert')).toHaveTextContent(/Network issue/)
  await user.click(screen.getByRole('button', { name: 'Send verification email' }))
  expect(screen.getByRole('button', { name: 'Try again in 60s' })).toBeDisabled()
  vi.setSystemTime(new Date(Date.now() + 60_000))
  await user.click(await screen.findByRole('button', { name: 'Resend verification email' }, { timeout: 2000 }))
  expect(sendVerification).toHaveBeenCalledTimes(3)
})
it.each(origins)('F11-2, F11-6: Continue opens the preserved creation destination (%s)', async (destination) => {
  const user = userEvent.setup()
  const { router } = renderVerification({ path: verificationUrl(destination) })
  await user.click(await screen.findByRole('link', { name: 'Continue' }))
  expect(router.state.location.pathname).toBe(destination.split('?')[0])
  expect(await screen.findByLabelText('Start time')).toBeVisible()
  expect(screen.getByRole('heading', { name: destination.startsWith('/need-a-sub') ? 'Create Sub Post' : 'Create Game', exact: true })).toBeVisible()
})
it.each(origins)('F11-2, F11-6: verification preserves entered creation form values (%s)', async (destination) => {
  const user = userEvent.setup()
  const view = renderVerification({ path: destination, verified: true })
  await user.selectOptions(await screen.findByLabelText('Start time'), '20:00')
  if (destination === '/create-game') await user.selectOptions(screen.getByLabelText('Total spots'), '18')
  server.verified = false
  firebaseUser.emailVerified = false
  await view.refreshAccount()
  await user.click(await screen.findByRole('button', { name: 'Send verification email' }))
  await navigate(view.router, verificationUrl(destination))
  await user.click(await screen.findByRole('link', { name: 'Continue' }))
  expect(await screen.findByLabelText('Start time')).toHaveValue('20:00')
  if (destination === '/create-game') expect(screen.getByLabelText('Total spots')).toHaveValue('18')
})
it.each(origins)('F11-7: an already verified account continues from a used link without signing in (%s)', async (destination) => {
  const user = userEvent.setup()
  vi.mocked(applyCode).mockRejectedValue(firebaseError('auth/invalid-action-code'))
  const { router } = renderVerification({ path: verificationUrl(destination), verified: true })
  await user.click(await screen.findByRole('link', { name: 'Continue' }))
  expect(await screen.findByLabelText('Start time')).toBeVisible()
  expect(router.state.location.pathname).not.toBe('/sign-in')
})
it('F11-6: account verification unlocks both creation forms without a second verification', async () => {
  const user = userEvent.setup()
  const view = renderVerification({ path: verificationUrl(origins[1]) })
  await user.click(await screen.findByRole('link', { name: 'Continue' }))
  expect(await screen.findByLabelText('Start time')).toBeVisible()
  await navigate(view.router, '/create-game')
  expect(await screen.findByLabelText('Start time')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Send verification email' })).not.toBeInTheDocument()
  expect(applyCode).toHaveBeenCalledTimes(1)
})
it.each(origins)('F11-1, F11-6: verification and return never publish automatically (%s)', async (destination) => {
  const user = userEvent.setup()
  renderVerification({ path: verificationUrl(destination) })
  await user.click(await screen.findByRole('link', { name: 'Continue' }))
  await screen.findByLabelText('Start time')
  const mutations = vi.mocked(apiRequestMock).mock.calls.filter(([path, options]) =>
    options?.method === 'POST' && ['/community-games/publish', '/need-a-sub/posts'].includes(path))
  expect(mutations).toEqual([])
})
it.each(origins)('F11-6: verification never restores another account form (%s)', async (destination) => {
  const user = userEvent.setup()
  const view = renderVerification({ path: destination, verified: true })
  await user.selectOptions(await screen.findByLabelText('Start time'), '20:00')
  if (destination === '/create-game') await user.selectOptions(screen.getByLabelText('Total spots'), '18')
  server.verified = false
  firebaseUser.emailVerified = false
  await view.refreshAccount()
  await user.click(await screen.findByRole('button', { name: 'Send verification email' }))
  view.unmount()
  firebaseUser.uid = 'a-different-synthetic-account'
  firebaseAuth.currentUser = firebaseUser
  renderVerification({ path: `${destination}${destination.includes('?') ? '&' : '?'}verification=return`, verified: true })
  expect(await screen.findByLabelText('Start time')).not.toHaveValue('20:00')
})
it.each(['https://outside.example/create-game', '//outside.example/create-game', '/admin', '/need-a-sub?panel=mine', '/create-game/../admin'])('F11-2, F11-6: unsafe or unsupported returns use the existing creation entry (%s)', async (destination) => {
  const path = `/reset-password?mode=verifyEmail&oobCode=code&continueUrl=${encodeURIComponent(destination)}`
  renderVerification({ path })
  expect(await screen.findByRole('link', { name: 'Continue' })).toHaveAttribute('href', '/create-game?verification=return')
})
