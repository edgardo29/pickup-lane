import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'
import { confirmPasswordReset, sendPasswordResetEmail } from 'firebase/auth'
import { auth } from '../../../src/lib/firebase.js'
import { AuthContext } from '../../../src/context/authContext.js'
import { buildAuthProviderCredentialActions } from '../../../src/context/authProviderCredentialActions.js'
import { CheckEmailPage } from '../../../src/pages/auth/CheckEmailPage.jsx'
import { ForgotPasswordPage } from '../../../src/pages/auth/ForgotPasswordPage.jsx'

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

export function renderForgotPassword() {
  const router = createMemoryRouter(
    [
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/check-email', element: <CheckEmailPage /> },
      { path: '/sign-in', element: <h1>Sign In</h1> },
    ],
    { initialEntries: ['/forgot-password'] },
  )
  render(
    <AuthContext.Provider value={buildAuthProviderCredentialActions({})}>
      <RouterProvider router={router} />
    </AuthContext.Provider>,
  )
  return router
}

export async function submitReset(user, email = 'player@example.com') {
  if (email) {
    await user.type(screen.getByRole('textbox', { name: 'Email' }), email)
  }
  await user.click(screen.getByRole('button', { name: 'Send Reset Link' }))
}

export const firebaseAuth = auth
export const buildCredentialActions = buildAuthProviderCredentialActions
export const updatePassword = confirmPasswordReset
export const requestResetEmail = sendPasswordResetEmail
