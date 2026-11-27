import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GAME_ID, fakeInboxApi, feed, gameItem, renderInbox, setAuth } from './inboxTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()), apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => setAuth())

const READ_ITEM = { is_new: false, read_at: '2030-06-15T18:01:00Z' }

function viewGameAction(overrides = {}) {
  return {
    key: 'view_game',
    label: 'View game',
    path: `/games/${GAME_ID}`,
    disabled: false,
    disabled_reason: null,
    state: null,
    ...overrides,
  }
}

async function openGameNotice(user, item) {
  fakeInboxApi({ 'GET /inbox/game-activity': feed([item]) })
  const view = renderInbox()
  await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
  await user.click(await screen.findByRole('button', { name: /Game updated/ }))
  return view
}

describe('Inbox modal actions', () => {
  it('F25-5: choosing an available action opens the named destination', async () => {
    const user = userEvent.setup()
    const { router } = await openGameNotice(user, gameItem({ ...READ_ITEM, action: viewGameAction() }))

    await user.click(screen.getByRole('button', { name: 'View game' }))

    expect(await screen.findByRole('heading', { name: 'Game Details' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(`/games/${GAME_ID}`)
  })

  it('F25-5: closing the modal instead leaves the user in Inbox', async () => {
    const user = userEvent.setup()
    const { router } = await openGameNotice(user, gameItem({ ...READ_ITEM, action: viewGameAction() }))

    await user.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/inbox')
  })

  it('F25-6: a notification with no action shows its text and no action button', async () => {
    const user = userEvent.setup()
    await openGameNotice(user, gameItem({ ...READ_ITEM, action: null }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByText('The start time changed. Review the latest game details.')).toBeInTheDocument()
    expect(within(dialog).getAllByRole('button').map((button) => button.textContent)).toEqual(['', 'Back'])
  })

  it('F25-6: a disabled action shows its reason and does not navigate', async () => {
    const user = userEvent.setup()
    const { router } = await openGameNotice(user, gameItem({
      ...READ_ITEM,
      action: viewGameAction({
        path: null,
        disabled: true,
        disabled_reason: 'You no longer have access to this game.',
      }),
    }))

    const action = screen.getByRole('button', { name: 'View game' })
    expect(action).toBeDisabled()
    expect(screen.getByText('You no longer have access to this game.')).toBeInTheDocument()
    await user.click(action)
    expect(router.state.location.pathname).toBe('/inbox')
  })
})
