import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { firebaseAuth as auth, sdkEmail, sdkGoogle, sdkCreate, server, renderSignIn, signIn, ready, at, error, firebaseError, firebaseUser, deferred, settle, credentialWhenReady, GAME_PATH } from './signInTestKit.jsx'

it('F07-1, F07-2: visitors can choose either sign-in method', async () => {
  renderSignIn(); await ready()
  expect(screen.getByLabelText('Email')).toBeInTheDocument()
  expect(screen.getByLabelText(/^Password/, { selector: 'input' })).toHaveAttribute('type', 'password')
  expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeEnabled()
})
it('F07-1: password visibility keeps the entered value', async () => {
  renderSignIn(); await ready(); const user = userEvent.setup()
  const input = screen.getByLabelText(/^Password/, { selector: 'input' })
  await user.type(input, 'synthetic-pass-1'); await user.click(screen.getByRole('button', { name: 'Show password' }))
  expect(input).toHaveAttribute('type', 'text'); expect(input).toHaveValue('synthetic-pass-1')
  await user.click(screen.getByRole('button', { name: 'Hide password' }))
  expect(input).toHaveAttribute('type', 'password'); expect(input).toHaveValue('synthetic-pass-1')
})
it.each([undefined, GAME_PATH])('F07-1: email sign-in opens its saved destination or discovery (%s)', async (from) => {
  const router = renderSignIn({ from }); await signIn(); await at(router, from || '/games')
  expect(sdkEmail).toHaveBeenCalledWith(auth, 'signin@example.test', 'synthetic-pass-1')
  expect(screen.getByLabelText('Current account')).toHaveTextContent('signin@example.test')
})
it.each([undefined, GAME_PATH])('F07-2: Google sign-in opens its saved destination or discovery (%s)', async (from) => {
  const router = renderSignIn({ from }); await signIn('google'); await at(router, from || '/games')
  expect(sdkGoogle).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('Current account')).toHaveTextContent('signin@example.test')
})
it('F07-2: existing Google sign-in reuses the Firebase identity', async () => {
  const router = renderSignIn(); await signIn('google'); await at(router, '/games')
  expect(sdkCreate).not.toHaveBeenCalled()
  expect(sdkGoogle).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('Current account')).toHaveTextContent('signin@example.test')
})
it('F07-4: Forgot opens Forgot Password', async () => {
  const router = renderSignIn(); await ready(); await userEvent.setup().click(screen.getByRole('link', { name: 'Forgot?' }))
  await at(router, '/forgot-password'); expect(screen.getByRole('heading', { name: /Forgot password/i })).toBeInTheDocument()
})
it('F07-4: switching to Create Account and back retains the destination', async () => {
  const router = renderSignIn({ from: GAME_PATH }); await ready(); const user = userEvent.setup()
  await user.click(screen.getByRole('link', { name: 'Create Account' })); await at(router, '/create-account')
  expect(router.state.location.state.from).toBe(GAME_PATH)
  await user.click(screen.getByRole('link', { name: 'Sign In' })); await at(router, '/sign-in')
  expect(router.state.location.state.from).toBe(GAME_PATH)
})
it('F07-5: password-changed confirmation is announced', async () => {
  renderSignIn({ path: '/sign-in?reset=success' }); await ready()
  expect(screen.getByText('Password changed.')).toHaveAttribute('role', 'status')
})
it('F07-6: invalid email has associated inline feedback without authentication', async () => {
  renderSignIn(); await ready(); const user = userEvent.setup()
  await user.type(screen.getByLabelText('Email'), 'invalid'); await user.click(screen.getByRole('button', { name: 'Sign In' }))
  expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')
  expect(screen.getByLabelText('Email')).toHaveAccessibleDescription('Enter a valid email.')
  expect(sdkEmail).not.toHaveBeenCalled()
})
it('F07-6: missing password has associated inline feedback without authentication', async () => {
  renderSignIn(); await ready(); const user = userEvent.setup()
  await user.type(screen.getByLabelText('Email'), 'signin@example.test'); await user.click(screen.getByRole('button', { name: 'Sign In' }))
  const input = screen.getByLabelText(/^Password/, { selector: 'input' })
  expect(input).toHaveAttribute('aria-invalid', 'true'); expect(input).toHaveAccessibleDescription('Enter your password.')
  expect(sdkEmail).not.toHaveBeenCalled()
})
it.each(['auth/user-not-found', 'auth/wrong-password', 'auth/invalid-credential'])('F07-7: incorrect credentials use the same non-disclosing error (%s)', async (code) => {
  vi.mocked(sdkEmail).mockRejectedValueOnce(firebaseError(code)); renderSignIn(); await signIn()
  expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is incorrect.')
  expect(screen.getByRole('button', { name: 'Sign In' })).toBeEnabled()
})
it('F07-8: Google cancellation is recoverable without success', async () => {
  vi.mocked(sdkGoogle).mockRejectedValueOnce(firebaseError('auth/popup-closed-by-user'))
  const router = renderSignIn(); await signIn('google')
  expect(await screen.findByRole('alert')).toHaveTextContent(/cancel/i)
  expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeEnabled()
  expect(router.state.location.pathname).toBe('/sign-in')
})
it.each(['firebase', 'account'])('F07-8: connection failure allows a successful retry (%s)', async (source) => {
  if (source === 'firebase') vi.mocked(sdkEmail).mockRejectedValueOnce(firebaseError('auth/network-request-failed'))
  else server.accountError = error('Could not reach the server.', 503)
  const router = renderSignIn(); await signIn(); expect(await screen.findByRole('alert')).toBeInTheDocument()
  await ready(); expect(router.state.location.pathname).toBe('/sign-in')
  expect(screen.getByLabelText('Current account')).toHaveTextContent('Signed out')
  server.accountError = null; await userEvent.setup().click(screen.getByRole('button', { name: 'Sign In' })); await at(router, '/games')
})
it.each(['email', 'google'])('F07-10: both sign-in methods stay disabled during a pending action (%s)', async (method) => {
  const request = deferred(); vi.mocked(method === 'email' ? sdkEmail : sdkGoogle).mockReturnValueOnce(credentialWhenReady(request))
  renderSignIn(); await signIn(method)
  expect(screen.getByRole('button', { name: 'Signing in...' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeDisabled()
  await settle(request, { user: firebaseUser() })
})
it('F07-10: repeated pending submission starts only one authentication operation', async () => {
  const request = deferred(); vi.mocked(sdkEmail).mockReturnValueOnce(credentialWhenReady(request))
  const router = renderSignIn()
  const arrivals = new Set()
  router.subscribe(({ location }) => { if (location.pathname === '/games') arrivals.add(location.key) })
  await signIn()
  fireEvent.submit(screen.getByRole('button', { name: 'Signing in...' }).closest('form'))
  expect(sdkEmail).toHaveBeenCalledTimes(1)
  await settle(request, { user: firebaseUser() }); await at(router, '/games')
  expect(router.state.historyAction).toBe('REPLACE'); expect(sdkEmail).toHaveBeenCalledTimes(1)
  expect(arrivals.size).toBe(1)
})
