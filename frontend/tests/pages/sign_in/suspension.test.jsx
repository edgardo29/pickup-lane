import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { server, renderSignIn, signIn, at, account, unfinished, firebaseUser, error, GAME_PATH, http } from './signInTestKit.jsx'

it.each(['email', 'google'].flatMap((method) => [false, true].map((complete) => [method, complete])))('F07-12: suspension takes priority after sign-in (%s, complete=%s)', async (method, complete) => {
  server.account = (complete ? account : unfinished)({ account_status: 'suspended' })
  const router = renderSignIn({ from: GAME_PATH }); await signIn(method); await at(router, '/account-suspended')
  expect(await screen.findByRole('heading', { name: 'Account Suspended', level: 1 })).toBeInTheDocument()
})
it('F07-9: an already signed-in suspended account reaches its registered restricted page', async () => {
  server.account = account({ account_status: 'suspended' })
  const router = renderSignIn({ from: GAME_PATH, initialUser: firebaseUser(), realRoutes: true }); await at(router, '/account-suspended')
  expect(await screen.findByRole('heading', { name: 'Account Suspended', level: 1 })).toBeInTheDocument()
})
it('F07-12: suspension notice is available without Inbox', async () => {
  server.account = account({ account_status: 'suspended' }); renderSignIn({ path: '/account-suspended', initialUser: firebaseUser() })
  expect(await screen.findByText(server.notice.notice_message)).toBeInTheDocument()
  expect(http.mock.calls.some(([path]) => path.startsWith('/notifications'))).toBe(false)
})
it('F07-12: restrictions retain existing commitments without new participation', async () => {
  server.account = account({ account_status: 'suspended' }); renderSignIn({ path: '/account-suspended', initialUser: firebaseUser() })
  expect(await screen.findByText('Staff actions are unavailable.')).toBeInTheDocument()
  expect(screen.getByText('View and fulfill commitments you already accepted.')).toBeInTheDocument()
  expect(screen.getByText('Manage games you already host and your existing Need a Sub arrangements.')).toBeInTheDocument()
  expect(screen.getByText('Withdraw from an existing commitment.')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'View my games and Sub Post commitments' })).toHaveAttribute('href', '/my-games')
  expect(screen.queryByRole('link', { name: /Create|Join|Request/ })).not.toBeInTheDocument()
})
it('F07-12: notice failure keeps restrictions visible and offers a working retry', async () => {
  server.account = account({ account_status: 'suspended' }); server.noticeError = error('Service unavailable.', 503)
  renderSignIn({ path: '/account-suspended', initialUser: firebaseUser() })
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load'); expect(screen.getByText(/You cannot create a game or post/)).toBeInTheDocument()
  expect(screen.queryByText(server.notice.notice_message)).not.toBeInTheDocument(); server.noticeError = null
  await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText(server.notice.notice_message)).toBeInTheDocument()
})
it('F07-12: an absent notice is stated honestly', async () => {
  server.account = account({ account_status: 'suspended' }); server.noticeError = error('Suspension notice not found.', 404)
  renderSignIn({ path: '/account-suspended', initialUser: firebaseUser() })
  expect(await screen.findByText('No suspension notice is available. Contact support for help.')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Account suspended', level: 3 })).not.toBeInTheDocument()
})
