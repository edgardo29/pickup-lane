import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GAME_ID, USER_ID, fakeInboxApi, feed, gameItem, renderInbox, setAuth } from './inboxTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()), apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => setAuth())

const SUSPENSION_NOTICE = {
  account_status: 'suspended',
  notice_title: 'Account suspended',
  notice_message: 'Your account was suspended after a policy review.',
  notice_occurred_at: '2030-06-15T18:00:00Z',
}

function signInSuspended() {
  setAuth({ appUser: { id: USER_ID, account_status: 'suspended' } })
}

describe('Inbox access', () => {
  it('F25-12: a signed-out visitor is sent to Sign In', async () => {
    setAuth({ appUser: null, currentUser: null })
    fakeInboxApi()
    const { router } = renderInbox()

    expect(await screen.findByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/sign-in')
  })

  it('F25-13: a suspended user who opens Inbox reaches Account Suspended', async () => {
    signInSuspended()
    fakeInboxApi({ 'GET /account-suspended': SUSPENSION_NOTICE })
    const { router } = renderInbox()

    expect(await screen.findByRole('heading', { name: 'Account Suspended' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/account-suspended')
  })

  it('F25-13: Account Suspended shows the suspension notice and the restrictions', async () => {
    signInSuspended()
    fakeInboxApi({ 'GET /account-suspended': SUSPENSION_NOTICE })
    renderInbox('/account-suspended')

    expect(await screen.findByRole('heading', { name: 'Account suspended' })).toBeInTheDocument()
    expect(screen.getByText('Your account was suspended after a policy review.')).toBeInTheDocument()
    expect(screen.getByText('View and fulfill commitments you already accepted.')).toBeInTheDocument()
    expect(screen.getByText(
      'Manage games you already host and your existing Need a Sub arrangements.',
    )).toBeInTheDocument()
    expect(screen.getByText('Withdraw from an existing commitment.')).toBeInTheDocument()
    expect(screen.getByText(
      'You cannot create a game or post, register for another game, add guests, or start new participation.',
    )).toBeInTheDocument()
  })

  it('F25-14: the official-game change notice shows what changed, the choice to keep the booking or request removal, and View game', async () => {
    const user = userEvent.setup()
    const message = (
      'The start time changed after you booked. Review the latest details. You may keep '
      + 'your booking or request removal and choose a refund to the original payment method '
      + 'or Pickup Lane game credit. This notice does not change your booking or issue money.'
    )
    fakeInboxApi({
      'GET /inbox/game-activity': feed([gameItem({
        is_new: false,
        read_at: '2030-06-15T18:01:00Z',
        message,
        summary: 'The start time changed.',
        action: {
          key: 'view_game', label: 'View game', path: `/games/${GAME_ID}`,
          disabled: false, disabled_reason: null, state: null,
        },
      })]),
    })
    renderInbox()
    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
    await user.click(await screen.findByRole('button', { name: /Game updated/ }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText(message)).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'View game' })).toBeEnabled()
  })
})
