import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderCheckEmail } from './checkEmailTestKit.jsx'

describe('Check Email guidance', () => {
  it('F09-1: the page identifies the submitted email', () => {
    renderCheckEmail('visitor@example.com')

    expect(screen.getByText('visitor@example.com')).toBeVisible()
  })

  it.each(['known@example.com', 'unknown@example.com'])(
    'F09-1: confirmation does not reveal account existence (%s)', (email) => {
      renderCheckEmail(email)

      expect(screen.getByText(/If an account exists/)).toHaveTextContent(
        `If an account exists, we sent a password reset link to ${email}.`,
      )
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    },
  )

  it('F09-1: instructions say to check inbox and spam', () => {
    renderCheckEmail()

    expect(screen.getByText('Check your inbox and spam folder.')).toBeVisible()
  })

  it('F09-1: instructions say to open the email link and reset the password', () => {
    renderCheckEmail()

    expect(screen.getByText('Click the link in the email')).toBeVisible()
    expect(screen.getByText('to reset your password.')).toBeVisible()
  })

  it('F09-1: instructions state the 60-minute link expiry', () => {
    renderCheckEmail()

    expect(screen.getByText('The link will expire in 60 minutes')).toBeVisible()
  })

  it('F09-4: a direct visit shows general reset guidance', () => {
    renderCheckEmail(null)

    expect(screen.getByRole('heading', { name: 'Check your email' })).toBeVisible()
    expect(screen.getByText('If the email matches an account, a reset link is on the way.'))
      .toBeVisible()
    expect(screen.getByText('Check your inbox and spam folder.')).toBeVisible()
    expect(screen.getByText('Click the link in the email')).toBeVisible()
    expect(screen.getByText('to reset your password.')).toBeVisible()
  })
})
