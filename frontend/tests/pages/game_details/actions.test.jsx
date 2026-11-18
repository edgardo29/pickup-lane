import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest, ApiRequestError } from '../../../src/lib/apiClient.js'
import { communityGame, fakePageApi, game, GAME_ID, HOST_ID, participant, PLAYER_ID, renderGame } from './gameDetailsTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()),
  apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/pages/admin/shared/useAdminAccess.js', () => ({
  useAdminAccess: () => ({ hasAdminAccess: false }),
}))
vi.mock('../../../src/components/BrowseAppNav.jsx', () => ({ default: () => null }))

beforeEach(() => {
  vi.mocked(useAuth).mockReturnValue({
    appUser: { id: PLAYER_ID, first_name: 'Test', last_name: 'Player',
      date_of_birth: '1990-01-01', account_status: 'active' },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
})

describe('Game Details actions', () => {
  it('F16-7: leaving updates the roster only after the API succeeds', async () => {
    const user = userEvent.setup()
    let rosterLoads = 0
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': () => rosterLoads++ === 0 ? [participant()] : [],
      'POST /games/{game_id}/leave': {
        status: 'left', message: 'You left this game.', refund_eligible: false,
        participant_id: participant().id, booking_id: participant().booking_id,
      },
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    const dialog = screen.getByRole('dialog', { name: 'Edit attendance?' })
    expect(screen.getAllByLabelText('Joined status').length).toBeGreaterThan(0)
    await user.click(within(dialog).getByRole('button', { name: 'Leave Game' }))

    expect((await screen.findAllByRole('button', { name: 'Join Game' })).length).toBeGreaterThan(0)
    expect(screen.queryByRole('dialog', { name: 'Edit attendance?' })).not.toBeInTheDocument()
  })

  it('F16-17: a failed leave keeps the game and shows feedback', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /games/{game_id}/leave': new ApiRequestError('Attendance changed; try again', { status: 409 }),
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    await user.click(within(screen.getByRole('dialog', { name: 'Edit attendance?' })).getByRole('button', { name: 'Leave Game' }))

    expect(await screen.findByText('Attendance changed; try again')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.getAllByLabelText('Joined status').length).toBeGreaterThan(0)
  })

  it('F16-19: an unverified-email rejection keeps the existing booking visible', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /games/{game_id}/leave': new ApiRequestError('Verified email required.', { status: 403 }),
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    await user.click(within(screen.getByRole('dialog', { name: 'Edit attendance?' })).getByRole('button', { name: 'Leave Game' }))

    expect(await screen.findByText('Verified email required.')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Joined status').length).toBeGreaterThan(0)
  })

  it('F16-8: cancelling the host guest modal makes no request', async () => {
    const user = userEvent.setup()
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: HOST_ID, first_name: 'Host', last_name: 'User',
        date_of_birth: '1990-01-01', account_status: 'active' },
      currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
      isLoading: false,
    })
    fakePageApi(communityGame({ is_chat_enabled: false }))
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: /Manage Guests/ })[0])
    const dialog = screen.getByRole('dialog', { name: 'Manage Guests' })
    await user.click(within(dialog).getByRole('button', { name: 'Add one guest' }))
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog', { name: 'Manage Guests' })).not.toBeInTheDocument()
    expect(apiRequest).not.toHaveBeenCalledWith(`/games/${GAME_ID}/guests/add`, expect.anything())
  })

  it('F16-9: a host confirms cancellation and then sees the cancelled state', async () => {
    const user = userEvent.setup()
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: HOST_ID, first_name: 'Host', last_name: 'User',
        date_of_birth: '1990-01-01', account_status: 'active' },
      currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
      isLoading: false,
    })
    const active = communityGame({ is_chat_enabled: false })
    const cancelled = communityGame({ is_chat_enabled: false, game_status: 'cancelled',
      cancelled_at: '2029-06-15T20:00:00Z' })
    let gameLoads = 0
    fakePageApi(active, {
      'GET /games/{game_id}': () => gameLoads++ === 0 ? active : cancelled,
      'POST /games/{game_id}/cancel': cancelled,
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Cancel Game' })[0])
    const dialog = screen.getByRole('dialog', { name: 'Cancel game?' })
    await user.click(within(dialog).getByRole('button', { name: 'Cancel Game' }))

    expect(await screen.findByText('Game cancelled. Players were notified.')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Cancelled status').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
  })

  it('F16-7: adding booking guests opens checkout without changing attendance first', async () => {
    const user = userEvent.setup()
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant()],
    })
    const router = renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    const dialog = screen.getByRole('dialog', { name: 'Edit attendance?' })
    await user.click(within(dialog).getByRole('button', { name: 'Increase guests' }))
    await user.click(within(dialog).getByRole('button', { name: 'Continue to Checkout' }))

    expect(await screen.findByRole('heading', { name: 'Game Checkout' })).toBeInTheDocument()
    expect(router.state.location.search).toBe('?mode=add-guests&guest_count=1')
    expect(apiRequest).not.toHaveBeenCalledWith(`/games/${GAME_ID}/booking-guests/add`, expect.anything())
  })

  it('F16-7: removing a booking guest refreshes attendance after success', async () => {
    const user = userEvent.setup()
    const owner = participant()
    const guest = participant({
      id: '00000000-0000-4000-8000-000000000009', participant_type: 'guest',
      user_id: null, guest_of_user_id: PLAYER_ID, display_name_snapshot: 'Guest Player',
      roster_order: 2,
    })
    let rosterLoads = 0
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': () => rosterLoads++ === 0 ? [owner, guest] : [owner],
      'POST /games/{game_id}/guests/remove': {
        status: 'guests_removed', message: 'Guests removed.', removed_count: 1,
        booking_id: owner.booking_id,
      },
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    const dialog = screen.getByRole('dialog', { name: 'Edit attendance?' })
    await user.click(within(dialog).getByRole('button', { name: 'Decrease guests' }))
    await user.click(within(dialog).getByRole('button', { name: 'Update Guests' }))

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Edit attendance?' })).not.toBeInTheDocument()
    expect(apiRequest).toHaveBeenCalledWith(`/games/${GAME_ID}/guests/remove`, expect.objectContaining({
      method: 'POST', body: JSON.stringify({ remove_count: 1 }),
    }))
    expect(rosterLoads).toBe(2)
  })

  it('F16-8: saving host guests updates occupancy after the API succeeds', async () => {
    const user = userEvent.setup()
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: HOST_ID, first_name: 'Host', last_name: 'User',
        date_of_birth: '1990-01-01', account_status: 'active' },
      currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
      isLoading: false,
    })
    const hostParticipant = participant({
      participant_type: 'host', user_id: HOST_ID, booking_id: null,
    })
    const hostGuest = participant({
      id: '00000000-0000-4000-8000-000000000009', participant_type: 'guest',
      user_id: null, guest_of_user_id: HOST_ID, booking_id: null,
      display_name_snapshot: 'Host Guest', roster_order: 2,
    })
    let rosterLoads = 0
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': () => rosterLoads++ === 0 ? [hostParticipant] : [hostParticipant, hostGuest],
      'POST /games/{game_id}/guests/add': {
        status: 'guests_added', message: 'Host guests added.', added_count: 1,
      },
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: /Manage Guests/ })[0])
    const dialog = screen.getByRole('dialog', { name: 'Manage Guests' })
    await user.click(within(dialog).getByRole('button', { name: 'Add one guest' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save Changes' }))

    expect(await screen.findByLabelText('1 of 2 host guests added')).toBeInTheDocument()
    expect(rosterLoads).toBe(2)
    expect(apiRequest).toHaveBeenCalledWith(`/games/${GAME_ID}/guests/add`, expect.objectContaining({
      method: 'POST', body: JSON.stringify({ guest_count: 1 }),
    }))
  })

  it('F16-15: a host guest addition rejected after the last spot was taken shows the error and changes nothing', async () => {
    const user = userEvent.setup()
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: HOST_ID, first_name: 'Host', last_name: 'User',
        date_of_birth: '1990-01-01', account_status: 'active' },
      currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
      isLoading: false,
    })
    const hostParticipant = participant({
      participant_type: 'host', user_id: HOST_ID, booking_id: null,
    })
    // The page still shows open spots, but a player took the last one first.
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [hostParticipant],
      'POST /games/{game_id}/guests/add': new ApiRequestError(
        'Not enough spots are available for host guests.', { status: 400 },
      ),
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: /Manage Guests/ })[0])
    const dialog = screen.getByRole('dialog', { name: 'Manage Guests' })
    await user.click(within(dialog).getByRole('button', { name: 'Add one guest' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save Changes' }))

    expect(await screen.findByText('Not enough spots are available for host guests.')).toBeInTheDocument()
    expect(screen.queryByLabelText('1 of 2 host guests added')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
  })

  it('F16-11: Share Game copies the game link and the policy opens in a dismissible modal', async () => {
    const user = userEvent.setup()
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()
    fakePageApi(game({ is_chat_enabled: false }))
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Share Game' })[0])
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/games/${GAME_ID}`)
    await user.click(screen.getAllByRole('button', { name: 'View full policy' })[0])
    const dialog = screen.getByRole('dialog', { name: 'Cancellation and Refund Policy' })
    expect(dialog).toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Close Cancellation and Refund Policy' }))
    expect(screen.queryByRole('dialog', { name: 'Cancellation and Refund Policy' })).not.toBeInTheDocument()
  })
})
