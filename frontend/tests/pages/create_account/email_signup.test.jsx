import { fireEvent, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { at, beginEmail, count, deferred, EMAIL, error, GAME_PATH, go, http, PASSWORD, ready, renderSignup, sdkCreate, sdkGoogle, server, settle } from './createAccountTestKit.jsx'

it.each([undefined, GAME_PATH])('F05-1: valid email signup opens Finish Profile with its destination (%s)', async (from) => {
  const router = renderSignup({ from }); await beginEmail('  Signup@Example.test  '); await at(router, '/finish-profile')
  expect(router.state.location.state.from).toBe(from || '')
  expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
})
it('F05-1: the email step creates no Firebase identity or application account', async () => {
  const router = renderSignup(); await beginEmail(); await at(router, '/finish-profile')
  expect(sdkCreate).not.toHaveBeenCalled(); expect(sdkGoogle).not.toHaveBeenCalled()
  expect(http.mock.calls.map(([path, options]) => [options?.method || 'GET', path.split('?')[0]])).toEqual([['GET', '/auth/email-availability']])
  expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Pending')
  expect(server.account).toBeNull()
  expect(Object.values(window.localStorage)).not.toContain(PASSWORD)
  expect(Object.values(window.sessionStorage)).not.toContain(PASSWORD)
})
it.each(['invalid', 'person@', '@example.test'])('F05-5: invalid email does not advance (%s)', async (email) => {
  const router = renderSignup(); await beginEmail(email)
  expect(await screen.findByText('Enter a valid email.')).toBeInTheDocument()
  expect(router.state.location.pathname).toBe('/create-account'); expect(http).not.toHaveBeenCalled()
})
it('F05-5: a blank password does not advance', async () => {
  const router = renderSignup(); await beginEmail(EMAIL, '')
  expect(await screen.findByText('Create a password.')).toBeInTheDocument()
  expect(router.state.location.pathname).toBe('/create-account'); expect(http).not.toHaveBeenCalled()
})
it.each(['short1', 'abcdefgh'])('F05-5: a weak password does not advance (%s)', async (password) => {
  const router = renderSignup(); await beginEmail(EMAIL, password)
  expect(await screen.findByText('Password must be at least 8 characters and include a number or symbol.')).toBeInTheDocument()
  expect(router.state.location.pathname).toBe('/create-account'); expect(http).not.toHaveBeenCalled()
})
it('F05-6: an already-used email cannot start another signup', async () => {
  server.available = false; const router = renderSignup(); await beginEmail()
  expect(await screen.findByText('An account already exists with this email.')).toBeInTheDocument()
  expect(router.state.location.pathname).toBe('/create-account')
  expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Empty'); expect(sdkCreate).not.toHaveBeenCalled()
})
it('F05-7: an availability failure retains the form and permits retry', async () => {
  server.availabilityError = error('Could not check email availability. Please try again.')
  const router = renderSignup(); await beginEmail()
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not check this email. Please try again.')
  expect(screen.getByLabelText('Email')).toHaveValue(EMAIL); expect(screen.getByLabelText(/^Password/, { selector: 'input' })).toHaveValue(PASSWORD)
  expect(router.state.location.pathname).toBe('/create-account')
  server.availabilityError = null; await userEvent.setup().click(screen.getByRole('button', { name: 'Create Account' })); await at(router, '/finish-profile')
})
it('F05-8: refreshing the email flow creates no account and forgets its credentials', async () => {
  const router = renderSignup(); await beginEmail(); await at(router, '/finish-profile'); router.view.unmount()
  const refreshed = renderSignup({ path: '/finish-profile' }); await at(refreshed, '/create-account'); await ready()
  expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Empty')
  expect(screen.getByLabelText('Email')).toHaveValue(''); expect(sdkCreate).not.toHaveBeenCalled()
  expect(count('/auth/sync-user', 'POST')).toBe(0); expect(server.account).toBeNull()
})
it.each(['/create-account', '/finish-profile'])('F05-8: leaving signup clears credentials without creating an account (%s)', async (leaveFrom) => {
  const router = renderSignup(); await beginEmail(); await at(router, '/finish-profile')
  if (leaveFrom === '/create-account') await go(router, '/create-account')
  await go(router, '/games')
  expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Empty')
  expect(sdkCreate).not.toHaveBeenCalled(); expect(count('/auth/sync-user', 'POST')).toBe(0); expect(server.account).toBeNull()
})
it('F05-1, F05-7: pending availability disables both methods and prevents another request', async () => {
  const request = deferred(); http.mockReturnValueOnce(request.promise)
  const router = renderSignup(); await beginEmail()
  const button = screen.getByRole('button', { name: 'Checking...' })
  expect(button).toBeDisabled(); expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeDisabled()
  fireEvent.submit(button.closest('form'))
  expect(count('/auth/email-availability')).toBe(1); expect(sdkGoogle).not.toHaveBeenCalled()
  await settle(request, { email: EMAIL, available: true }); await at(router, '/finish-profile')
})
it('F05-8: a late availability result cannot navigate or retain credentials after leaving', async () => {
  const request = deferred(); http.mockReturnValueOnce(request.promise)
  const router = renderSignup(); await beginEmail(); await go(router, '/games')
  await settle(request, { email: EMAIL, available: true })
  expect(router.state.location.pathname).toBe('/games'); expect(screen.getByLabelText('Signup draft')).toHaveTextContent('Empty')
})
it.each([['invalid', PASSWORD, 'Email', 'Enter a valid email.'], [EMAIL, '', 'Password', 'Create a password.']])('F05-5: validation is associated with the invalid field (%s, %s)', async (email, password, label, message) => {
  renderSignup(); await beginEmail(email, password)
  const input = screen.getByLabelText(new RegExp(`^${label}`), { selector: 'input' })
  expect(input).toHaveAttribute('aria-invalid', 'true'); expect(input).toHaveAccessibleDescription(message)
})
it.each(['used', 'unavailable'])('F05-6, F05-7: signup failures are announced (%s)', async (failure) => {
  if (failure === 'used') server.available = false
  else server.availabilityError = error('Could not check email availability. Please try again.')
  const router = renderSignup(); await beginEmail()
  expect(await screen.findByRole('alert')).toHaveTextContent(failure === 'used' ? 'An account already exists with this email.' : 'Could not check this email. Please try again.')
  expect(router.state.location.pathname).toBe('/create-account')
})
