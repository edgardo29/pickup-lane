import { screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { renderVerification } from './emailVerificationTestKit.jsx'

it.each([false, true])('F11-8: public game browsing does not require verification (signed in: %s)', async (signedIn) => {
  renderVerification({ path: '/games/browse', signedIn })
  expect(await screen.findByRole('link', { name: /Public Game Field/ })).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Send verification email' })).not.toBeInTheDocument()
})
it('F11-8: unverified signed-in accounts can browse public Sub Post cards', async () => {
  renderVerification({ path: '/need-a-sub' })
  expect(await screen.findByText('Public Sub Field')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Send verification email' })).not.toBeInTheDocument()
})
it('F11-8: signed-out visitors can browse public Sub Post cards', async () => {
  renderVerification({ path: '/need-a-sub', signedIn: false })
  expect(await screen.findByRole('button', { name: /^Need 1 Sub/ })).toBeVisible()
  expect(screen.getByText('Public Sub Field')).toBeVisible()
})
