import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { apiRequest } from '../../../src/lib/apiClient.js'
import { communityDetails, communityGame, fakePageApi, game, GAME_ID, HOST_ID, participant, PLAYER_ID, renderGame } from './gameDetailsTestKit.jsx'

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
  vi.mocked(useAuth).mockReturnValue({ appUser: null, currentUser: null, isLoading: false })
})

function signIn(id = PLAYER_ID, accountStatus = 'active') {
  vi.mocked(useAuth).mockReturnValue({
    appUser: { id, role: 'player', account_status: accountStatus,
      first_name: 'Test', last_name: 'Player', date_of_birth: '1990-01-01' },
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
  })
}

describe('Game Details page states', () => {
  it('F16-1: shows a public official game and prompts signed-out visitors to sign in for the roster', async () => {
    fakePageApi(game())
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign In' })).toBeInTheDocument()
    expect(screen.getByText('3/14')).toBeInTheDocument()
  })

  it('F16-27: shows community payment responsibility before the join control', async () => {
    fakePageApi(communityGame())
    renderGame()

    const notice = await screen.findByText(/Payment happens outside Pickup Lane/)
    expect(notice).toHaveTextContent(/original organizer/)
    expect(notice).toHaveTextContent(/does not process or guarantee refunds/)
    expect(screen.getAllByText('Join Game').length).toBeGreaterThan(0)
  })

  it('F16-24: a paused community game shows its paused state and no active join control', async () => {
    fakePageApi(communityGame({ join_enforcement_status: 'paused' }))
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.getByText(/Joining Temporarily Paused\. Existing participants/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Join Game' })).not.toBeInTheDocument()
  })

  it('F16-25: a resumed community game offers Join again', async () => {
    fakePageApi(communityGame({ join_enforcement_status: 'open' }))
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.getAllByText('Join Game').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Joining Temporarily Paused\. Existing participants/)).not.toBeInTheDocument()
  })

  it('F16-12: a missing or inaccessible game has the not-found state and Browse link', async () => {
    fakePageApi(new ApiRequestError('Not found', { status: 404 }))
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Game Not Found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to games' })).toHaveAttribute('href', '/games/browse')
    expect(screen.queryByRole('heading', { name: 'Could not load game' })).not.toBeInTheDocument()
  })

  it('F16-17: a server failure has a distinct load-error state', async () => {
    fakePageApi(new ApiRequestError('Service unavailable', { status: 503 }))
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Could not load game' })).toBeInTheDocument()
    expect(screen.getByText('Service unavailable')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Game Not Found' })).not.toBeInTheDocument()
  })

  it('F16-16: a cancelled game remains visible without a Join or chat action', async () => {
    fakePageApi(game({ game_status: 'cancelled', cancelled_at: '2029-06-15T20:00:00Z' }))
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Join Game' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /open chat/i })).toBeDisabled()
  })

  it('F16-21: a booked player reviews an edit and requests removal while the booking remains', async () => {
    const user = userEvent.setup()
    const firebaseUser = { getIdToken: vi.fn().mockResolvedValue('test-token') }
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: PLAYER_ID, role: 'user', account_status: 'active' },
      currentUser: firebaseUser,
      isLoading: false,
    })
    const request = {
      id: '00000000-0000-4000-8000-000000000005',
      booking_id: '00000000-0000-4000-8000-000000000006',
      relief_choice: 'game_credit',
      request_status: 'pending',
      submitted_at: '2029-06-15T20:00:00Z',
    }
    fakePageApi(game({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant()],
      'GET /games/{game_id}/change-review': {
        changes: [
          { field: 'title', before: 'Old title', after: 'Evening Pickup', changed_at: '2029-06-15T19:00:00Z' },
          // 7 PM and 8 PM in Chicago, the game's time zone.
          { field: 'starts_at', before: '2029-06-16T00:00:00Z', after: '2029-06-16T01:00:00Z', changed_at: '2029-06-15T19:00:00Z' },
        ],
        active_request: null,
        can_request_removal: true,
      },
      'POST /games/{game_id}/change-removal-requests': request,
    })
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Game details changed' })).toBeInTheDocument()
    expect(screen.getByText(/Old title.*Evening Pickup/)).toBeInTheDocument()
    expect(screen.getByText(/7:00 PM.*8:00 PM/)).toBeInTheDocument()
    await user.click(screen.getByLabelText('Game credit'))
    await user.click(screen.getByRole('button', { name: 'Request to leave' }))

    expect(await screen.findByText(/Your request to leave is waiting for staff/)).toBeInTheDocument()
    const changeCard = screen.getByRole('region', { name: 'Game details changed' })
    expect(within(changeCard).getAllByRole('status')).toHaveLength(1)
    expect(screen.getByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(apiRequest).toHaveBeenCalledWith(`/games/${GAME_ID}/change-removal-requests`, expect.objectContaining({
      method: 'POST', body: JSON.stringify({ relief_choice: 'game_credit' }),
    }))
  })

  it('F16-21: a signed-in visitor without a booking is not checked for changes', async () => {
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: PLAYER_ID, role: 'user', account_status: 'active' },
      currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
      isLoading: false,
    })
    fakePageApi(game({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [],
    })
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.queryByText(/Checking for changes/)).not.toBeInTheDocument()
    expect(apiRequest).not.toHaveBeenCalledWith(`/games/${GAME_ID}/change-review`, expect.anything())
  })

  it('F16-2: shows allowed community host payment details and omits hidden payment text', async () => {
    fakePageApi(communityGame({ description: 'Bring water', custom_rules_text: 'No cleats' }), {
      'GET /community-game-details': [communityDetails({
        payment_methods_snapshot: [{ type: 'venmo', value: '@organizer' }],
        payment_instructions_snapshot: 'Pay before kickoff',
      })],
    })
    renderGame()

    expect(await screen.findByText('Bring water')).toBeInTheDocument()
    expect(screen.getByText('No cleats')).toBeInTheDocument()
    expect(screen.getByText('@organizer')).toBeInTheDocument()
  })

  it('F16-5: a full game offers a waitlist only when enabled', async () => {
    fakePageApi(game({ total_spots: 3, waitlist_enabled: true,
      roster_counts: { occupied_spots: 3, spots_remaining: 0, waitlist_count: 0 },
    }))
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Join Waitlist' })[0]).toBeEnabled()
  })

  it('F16-5: a full game without waitlist does not offer a new party', async () => {
    fakePageApi(game({ total_spots: 3, waitlist_enabled: false,
      roster_counts: { occupied_spots: 3, spots_remaining: 0, waitlist_count: 0 },
    }))
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.queryByRole('button', { name: 'Join Waitlist' })).not.toBeInTheDocument()
  })

  it('F16-6: a confirmed player sees Joined and can edit attendance', async () => {
    signIn()
    fakePageApi(game({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant()],
    })
    renderGame()

    expect(await screen.findByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.getAllByLabelText('Joined status').length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Edit Attendance' }).length).toBeGreaterThan(0)
  })

  it('F16-20: a suspended confirmed player retains Edit Attendance and cannot add guests', async () => {
    const user = userEvent.setup()
    signIn(PLAYER_ID, 'suspended')
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant()],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    expect(screen.getByRole('dialog', { name: 'Edit attendance?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Increase guests' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Leave Game' })).toBeEnabled()
  })

  it('F16-24: a paused existing player can leave but cannot add booking guests', async () => {
    const user = userEvent.setup()
    signIn()
    fakePageApi(communityGame({ is_chat_enabled: false, join_enforcement_status: 'paused' }), {
      'GET /games/{game_id}/participants': [participant()],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getByText(/Joining Temporarily Paused\. Existing participants/)).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    expect(screen.getByRole('button', { name: 'Increase guests' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Leave Game' })).toBeEnabled()
  })

  it('F16-6: a host sees Hosting and can manage an existing community game', async () => {
    signIn(HOST_ID, 'suspended')
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getAllByLabelText('Hosting status').length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: /Manage Guests/ }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Cancel Game' }).length).toBeGreaterThan(0)
  })

  it('F16-6: a waitlisted player sees Waitlisted and can leave the waitlist', async () => {
    signIn()
    fakePageApi(communityGame({ is_chat_enabled: false }), {
      'GET /games/{game_id}/participants': [participant({
        participant_status: 'waitlisted', confirmed_at: null,
      })],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getAllByLabelText('Waitlisted status').length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Leave Waitlist' }).length).toBeGreaterThan(0)
  })

  it('F16-4: signed-out Join goes to account creation with the game return path', async () => {
    const user = userEvent.setup()
    fakePageApi(game())
    const router = renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Join Game' })[0])

    expect(await screen.findByRole('heading', { name: 'Create Account' })).toBeInTheDocument()
    expect(router.state.location.state).toEqual({ from: `/games/${GAME_ID}` })
  })

  it('F16-4: an incomplete profile goes to Finish Profile before checkout', async () => {
    const user = userEvent.setup()
    vi.mocked(useAuth).mockReturnValue({
      appUser: { id: PLAYER_ID, first_name: 'Test', last_name: 'Player', date_of_birth: null },
      currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
      isLoading: false,
    })
    fakePageApi(game({ is_chat_enabled: false }))
    const router = renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Join Game' })[0])

    expect(await screen.findByRole('heading', { name: 'Finish Profile' })).toBeInTheDocument()
    expect(router.state.location.state).toEqual({ from: `/games/${GAME_ID}` })
  })

  it('F16-4: a complete player goes to checkout', async () => {
    const user = userEvent.setup()
    signIn()
    fakePageApi(game({ is_chat_enabled: false }))
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Join Game' })[0])

    expect(await screen.findByRole('heading', { name: 'Game Checkout' })).toBeInTheDocument()
  })

  it('F16-14: after the roster cutoff a visitor sees Join Closed', async () => {
    fakePageApi(game({
      starts_at: '2020-01-01T00:00:00Z',
      ends_at: '2020-01-01T01:00:00Z',
      starts_on_local: '2019-12-31',
    }))
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getAllByRole('button', { name: 'Join Closed' })[0]).toBeDisabled()
  })

  it('F16-23: community cancellation terms use organizer text or a non-promissory fallback', async () => {
    fakePageApi(communityGame({ custom_cancellation_text: 'Ask the organizer for changes.' }))
    renderGame()

    expect(await screen.findByText('Ask the organizer for changes.')).toBeInTheDocument()
    expect(screen.queryByText(/Players receive a refund or game credit/)).not.toBeInTheDocument()
  })

  it('F16-2: hidden payment text and absent optional notes leave no empty sections', async () => {
    fakePageApi(communityGame(), {
      'GET /community-game-details': [communityDetails({
        payment_methods_snapshot: [], payment_instructions_snapshot: null,
        payment_text_moderation_status: 'hidden',
      })],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.queryByRole('heading', { name: 'About This Game' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Host Rules' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Host Payment' })).not.toBeInTheDocument()
  })

  it('F16-23: missing organizer terms point to the host payment note without promising a refund', async () => {
    fakePageApi(communityGame({ custom_cancellation_text: null }))
    renderGame()

    expect(await screen.findByText(/Review the host payment note before canceling/)).toBeInTheDocument()
    expect(screen.queryByText(/Players receive a refund or game credit/)).not.toBeInTheDocument()
  })

  it('F16-20: a suspended nonparticipant cannot start a new join', async () => {
    signIn(PLAYER_ID, 'suspended')
    fakePageApi(communityGame({ is_chat_enabled: false }))
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getAllByRole('button', { name: 'Joining Unavailable' })[0]).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Join Game' })).not.toBeInTheDocument()
  })

  it('F16-25: after joining resumes, an existing player can start add-guest checkout', async () => {
    const user = userEvent.setup()
    signIn()
    fakePageApi(communityGame({ is_chat_enabled: false, join_enforcement_status: 'open' }), {
      'GET /games/{game_id}/participants': [participant()],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getAllByRole('button', { name: 'Edit Attendance' })[0])
    expect(screen.getByRole('button', { name: 'Increase guests' })).toBeEnabled()
  })

  it('F16-27: paid community games also show the responsibility notice before joining', async () => {
    fakePageApi(communityGame({ price_per_player_cents: 1500 }))
    renderGame()

    const notice = await screen.findByText(/Payment happens outside Pickup Lane/)
    expect(notice).toHaveTextContent(/original organizer/)
    const join = screen.getAllByRole('button', { name: 'Join Game' })[0]
    expect(notice.compareDocumentPosition(join) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('F16-28: a cancelled community game stays visible to a registered player without join or chat', async () => {
    signIn()
    fakePageApi(communityGame({
      game_status: 'cancelled', cancelled_at: '2029-06-15T20:00:00Z',
      host_user_id: null,
    }), {
      'GET /games/{game_id}/participants': [participant()],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getAllByLabelText('Cancelled status').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: 'Join Game' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open chat' })).toBeDisabled()
    expect(screen.getByText(/Payment happens outside Pickup Lane/)).toBeInTheDocument()
  })
})
