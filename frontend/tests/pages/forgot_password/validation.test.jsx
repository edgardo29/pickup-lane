import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import {
  renderForgotPassword,
  requestResetEmail as sendPasswordResetEmail,
  submitReset,
} from './forgotPasswordTestKit.jsx'

describe('Forgot Password local validation', () => {
  it.each([
    ['blank', ''],
    ['malformed', 'not-an-email'],
  ])('F08-4: a %s email shows associated inline validation', async (_case, email) => {
    const user = userEvent.setup()
    renderForgotPassword()
    const emailInput = screen.getByRole('textbox', { name: 'Email' })

    await submitReset(user, email)

    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a valid email.')
    expect(emailInput).toHaveAttribute('aria-invalid', 'true')
    expect(emailInput).toHaveAccessibleDescription('Enter a valid email.')
  })

  it.each([
    ['blank', ''],
    ['malformed', 'not-an-email'],
  ])('F08-4: a %s email sends no reset request', async (_case, email) => {
    const user = userEvent.setup()
    renderForgotPassword()

    await submitReset(user, email)

    expect(sendPasswordResetEmail).not.toHaveBeenCalled()
  })
})
