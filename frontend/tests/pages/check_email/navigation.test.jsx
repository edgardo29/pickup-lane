import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderCheckEmail } from './checkEmailTestKit.jsx'

describe('Check Email navigation', () => {
  it.each(['player@example.com', null])(
    'F09-3, F09-4: Forgot Password opens with or without retained email (%s)', async (email) => {
      const user = userEvent.setup()
      const router = renderCheckEmail(email)

      await user.click(screen.getByRole('link', { name: 'Didn’t receive the email?' }))

      expect(await screen.findByRole('heading', { name: 'Forgot Password' })).toBeVisible()
      expect(router.state.location.pathname).toBe('/forgot-password')
    },
  )

  it.each(['Back to sign in', 'Back to Sign In'])(
    'F09-3: the Sign In link opens Sign In (%s)', async (name) => {
      const user = userEvent.setup()
      const router = renderCheckEmail()

      await user.click(screen.getByRole('link', { name, exact: true }))

      expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeVisible()
      expect(router.state.location.pathname).toBe('/sign-in')
    },
  )
})
