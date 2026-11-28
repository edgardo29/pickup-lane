import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { account, at, beginGoogle, error, ready, renderSignup, server } from '../create_account/createAccountTestKit.jsx'

// Exercise Sign In after the real AuthProvider has cleaned up an unfinished signup.
it.each([false, true])('F07-2: Google sign-in works after signup cleanup (retry=%s)', async (retry) => {
  const router = renderSignup()
  await beginGoogle(); await at(router, '/finish-profile')
  const user = userEvent.setup()
  const back = await screen.findByRole('button', { name: 'Back to create account' })
  if (retry) server.cleanupError = error('Firebase could not clean up this sign-up. Please try again.', 502)
  await user.click(back)
  if (retry) {
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not cancel sign-up. Please try again.')
    server.cleanupError = null; await user.click(back)
  }
  await at(router, '/create-account'); await ready()
  server.account = account()
  await user.click(screen.getByRole('link', { name: 'Sign In' }))
  await at(router, '/sign-in')
  await user.click(await screen.findByRole('button', { name: 'Continue with Google' }))
  await at(router, '/games')
})
