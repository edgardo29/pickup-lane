import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'
import { confirmPasswordReset, sendPasswordResetEmail } from 'firebase/auth'
import { auth } from '../../../src/lib/firebase.js'
import { AuthContext } from '../../../src/context/authContext.js'
import { buildAuthProviderCredentialActions } from '../../../src/context/authProviderCredentialActions.js'
import { CheckEmailPage } from '../../../src/pages/auth/CheckEmailPage.jsx'

// Firebase is the only external service used by Check Email; no API answers are faked.
vi.mock('firebase/auth', async (importOriginal) => ({
  ...(await importOriginal()),
  confirmPasswordReset: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
}))
vi.mock('../../../src/lib/firebase.js', () => ({
  auth: { name: 'synthetic-auth' },
  ensureAuthPersistence: vi.fn(),
}))

beforeEach(() => {
  vi.stubGlobal('scrollTo', vi.fn())
  vi.mocked(sendPasswordResetEmail).mockResolvedValue(undefined)
  vi.mocked(confirmPasswordReset).mockResolvedValue(undefined)
})

export function renderCheckEmail(email = 'player@example.com') {
  const router = createMemoryRouter([
    { path: '/check-email', element: <CheckEmailPage /> },
    { path: '/forgot-password', element: <h1>Forgot Password</h1> },
    { path: '/sign-in', element: <h1>Sign In</h1> },
  ], {
    initialEntries: [{ pathname: '/check-email', state: email ? { email } : null }],
  })
  render(
    <AuthContext.Provider value={buildAuthProviderCredentialActions({})}>
      <RouterProvider router={router} />
    </AuthContext.Provider>,
  )
  return router
}

export async function resend(user) {
  await user.click(screen.getByRole('button', { name: /Resend email/ }))
}

export const firebaseAuth = auth
export const requestResetEmail = sendPasswordResetEmail
export const updatePassword = confirmPasswordReset
