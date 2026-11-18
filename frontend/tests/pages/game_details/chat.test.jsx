import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../../src/hooks/useAuth.js'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import { CHAT_ID, chatMessage, fakePageApi, game, gameChat, participant, PLAYER_ID, renderGame } from './gameDetailsTestKit.jsx'

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

describe('Game Details chat', () => {
  it('F16-3: a confirmed player can inspect the roster and open chat', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /game-chats/for-game/{game_id}': gameChat(),
      'GET /chat-messages': [],
      'POST /game-chats/{game_chat_id}/read': {
        chat_id: CHAT_ID, user_id: PLAYER_ID, last_read_at: '2029-06-15T18:00:00Z',
        last_read_message_id: null, unread_count: 0,
      },
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getByRole('button', { name: 'View player list' }))
    expect(within(screen.getByRole('dialog', { name: 'Players' })).getByText('Test Player')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close player list' }))
    await user.click(screen.getByRole('button', { name: 'Open chat' }))

    expect(await screen.findByRole('dialog', { name: 'Game Chat' })).toBeInTheDocument()
    expect(apiRequest).toHaveBeenCalledWith(`/game-chats/${CHAT_ID}/read`, expect.objectContaining({ method: 'POST' }))
  })

  it('F16-3: a waitlisted player can view names but cannot open chat', async () => {
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant({
        participant_status: 'waitlisted', confirmed_at: null,
      })],
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    expect(screen.getByRole('button', { name: 'View player list' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Open chat' })).toBeDisabled()
  })

  it('F16-10: a valid chat message appears after sending', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /game-chats/for-game/{game_id}': gameChat(),
      'GET /chat-messages': [],
      'POST /game-chats/{game_chat_id}/read': {
        chat_id: CHAT_ID, user_id: PLAYER_ID, last_read_at: '2029-06-15T18:00:00Z',
        last_read_message_id: null, unread_count: 0,
      },
      'POST /chat-messages': chatMessage({ message_body: 'Ready to play' }),
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getByRole('button', { name: 'Open chat' }))
    const dialog = await screen.findByRole('dialog', { name: 'Game Chat' })
    await user.type(within(dialog).getByRole('textbox', { name: 'Message' }), 'Ready to play')
    await user.click(within(dialog).getByRole('button', { name: 'Send' }))

    expect(await within(dialog).findByText('Ready to play')).toBeInTheDocument()
    expect(apiRequest).toHaveBeenCalledWith('/chat-messages', expect.objectContaining({
      method: 'POST', body: JSON.stringify({ chat_id: CHAT_ID, message_body: 'Ready to play' }),
    }))
  })

  it('F16-18: a rate-limited send shows an error without adding the message', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /game-chats/for-game/{game_id}': gameChat(),
      'GET /chat-messages': [],
      'POST /game-chats/{game_chat_id}/read': {
        chat_id: CHAT_ID, user_id: PLAYER_ID, last_read_at: '2029-06-15T18:00:00Z',
        last_read_message_id: null, unread_count: 0,
      },
      'POST /chat-messages': new ApiRequestError('Too many messages', { status: 429 }),
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getByRole('button', { name: 'Open chat' }))
    const dialog = await screen.findByRole('dialog', { name: 'Game Chat' })
    const messageBox = within(dialog).getByRole('textbox', { name: 'Message' })
    expect(within(dialog).getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(messageBox).toHaveAttribute('maxlength', '300')
    await user.type(messageBox, 'Slow down')
    await user.click(within(dialog).getByRole('button', { name: 'Send' }))

    expect(await within(dialog).findByText('Too many messages')).toBeInTheDocument()
    expect(dialog.querySelectorAll('.details-chat-message')).toHaveLength(0)
    expect(messageBox).toHaveValue('Slow down')
    await user.clear(messageBox)
    expect(within(dialog).getByRole('button', { name: 'Send' })).toBeDisabled()
    // Paste rather than type 301 keystrokes, which is slow enough to time out.
    await user.click(messageBox)
    await user.paste('x'.repeat(301))
    expect(messageBox.value).toHaveLength(300)
  })

  it('F16-19: an unverified player sees the server rejection without losing game details', async () => {
    const user = userEvent.setup()
    fakePageApi(game(), {
      'GET /games/{game_id}/participants': [participant()],
      'POST /game-chats/for-game/{game_id}': new ApiRequestError('Verify your email to use chat', { status: 403 }),
    })
    renderGame()

    await screen.findByRole('heading', { name: 'Evening Pickup' })
    await user.click(screen.getByRole('button', { name: 'Open chat' }))

    expect(await screen.findByText('Verify your email to use chat')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Evening Pickup' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog', { name: 'Game Chat' })).not.toBeInTheDocument()
  })
})
