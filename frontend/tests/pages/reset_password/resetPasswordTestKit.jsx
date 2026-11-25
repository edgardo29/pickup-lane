import { act, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, vi } from 'vitest'
import {
  applyActionCode, confirmPasswordReset, sendPasswordResetEmail,
  updatePassword, verifyPasswordResetCode,
} from 'firebase/auth'
import { auth } from '../../../src/lib/firebase.js'
import { useAuthProviderValue } from '../../../src/context/useAuthProviderValue.js'
import { AuthContext } from '../../../src/context/authContext.js'
import { buildAuthProviderCredentialActions } from '../../../src/context/authProviderCredentialActions.js'
import { ResetPasswordPage } from '../../../src/pages/auth/ResetPasswordPage.jsx'
import { ForgotPasswordPage } from '../../../src/pages/auth/ForgotPasswordPage.jsx'

vi.mock('firebase/auth', async (importOriginal) => ({
  ...(await importOriginal()),
  applyActionCode: vi.fn(),
  confirmPasswordReset: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
  updatePassword: vi.fn(),
  verifyPasswordResetCode: vi.fn(),
}))
vi.mock('../../../src/lib/firebase.js', () => ({
  auth: { name: 'synthetic-auth' },
  ensureAuthPersistence: vi.fn(),
}))

beforeEach(() => {
  vi.stubGlobal('scrollTo', vi.fn())
  vi.mocked(verifyPasswordResetCode).mockResolvedValue('player@example.com')
  vi.mocked(confirmPasswordReset).mockResolvedValue(undefined)
  vi.mocked(sendPasswordResetEmail).mockResolvedValue(undefined)
})

function createResetRouter(url) {
  return createMemoryRouter([
    { path: '/reset-password', element: <ResetPasswordPage /> },
    { path: '/forgot-password', element: <ForgotPasswordPage /> },
    { path: '/sign-in', element: <h1>Sign In</h1> },
  ], { initialEntries: [url] })
}

export function renderResetPassword(url = '/reset-password?oobCode=current-code') {
  const router = createResetRouter(url)
  render(
    <AuthContext.Provider value={buildAuthProviderCredentialActions({})}>
      <RouterProvider router={router} />
    </AuthContext.Provider>,
  )
  return router
}

function ResetAuthenticationState({ children, status }) {
  const value = useAuthProviderValue({ status })
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function renderResetWithAuthUpdates() {
  const router = createResetRouter('/reset-password?oobCode=current-code')
  const view = render(
    <ResetAuthenticationState status="loading">
      <RouterProvider router={router} />
    </ResetAuthenticationState>,
  )
  return async function finishAuthenticationLoading() {
    await act(async () => {
      view.rerender(
        <ResetAuthenticationState status="ready">
          <RouterProvider router={router} />
        </ResetAuthenticationState>,
      )
    })
  }
}

export function passwordInput() {
  return screen.getByLabelText(/^New password/)
}

export async function readyPasswordForm() {
  await screen.findByRole('heading', { name: 'Reset your password' })
  return passwordInput()
}

export async function savePassword(user, password = 'Newpass1') {
  await readyPasswordForm()
  await user.type(passwordInput(), password)
  await user.click(screen.getByRole('button', { name: 'Save Password' }))
}

export function deferred() {
  let resolve, reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

export async function settle(request, value, reject = false) {
  await act(async () => { request[reject ? 'reject' : 'resolve'](value) })
}

export async function navigate(router, url) {
  await act(async () => { await router.navigate(url) })
}

export function firebaseError(code) {
  return Object.assign(new Error(`Firebase: Error (${code}).`), { code })
}

// Firebase reports both an invalid code and a consumed code as invalid-action-code.
export const unavailableLinks = [
  ['missing', '', null, /missing or invalid/i],
  ['invalid', 'invalid-code', 'auth/invalid-action-code', /invalid or has already been used/i],
  ['expired', 'expired-code', 'auth/expired-action-code', /reset link expired/i],
  ['used', 'used-code', 'auth/invalid-action-code', /invalid or has already been used/i],
]
export function renderUnavailableLink(code, errorCode) {
  if (errorCode) vi.mocked(verifyPasswordResetCode).mockRejectedValueOnce(firebaseError(errorCode))
  return renderResetPassword(`/reset-password${code ? `?oobCode=${code}` : ''}`)
}
export const unusableSaveCodes = ['auth/expired-action-code', 'auth/invalid-action-code']
export const invalidPasswords = ['', 'Short1', 'abcdefgh']
export const saveErrors = [
  ['auth/network-request-failed', /Network issue/],
  ['auth/internal-error', /Something went wrong/],
  ['auth/weak-password', /Password must be at least 8 characters/],
]
export const firebaseAuth = auth
export const buildCredentialActions = buildAuthProviderCredentialActions
export const applyEmailCode = applyActionCode
export const confirmReset = confirmPasswordReset
export const requestReset = sendPasswordResetEmail
export const fallbackUpdate = updatePassword
export const checkResetCode = verifyPasswordResetCode
