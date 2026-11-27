import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  fakeInboxApi, feed, gameItem, inboxItem, itemId, renderInbox, requestCount, setAuth,
} from './inboxTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()), apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => setAuth())

function optionLabels(select) {
  return within(select).getAllByRole('option').map((option) => option.textContent)
}

describe('Inbox feeds', () => {
  it("F25-1: each tab shows only its own feed's rows", async () => {
    const user = userEvent.setup()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([inboxItem()]),
      'GET /inbox/game-activity': feed([gameItem()]),
    })
    renderInbox()

    expect(await screen.findByText('Account updated')).toBeInTheDocument()
    expect(screen.queryByText('Game updated')).not.toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
    expect(await screen.findByText('Game updated')).toBeInTheDocument()
    expect(screen.queryByText('Account updated')).not.toBeInTheDocument()
  })

  it('F25-1: each tab displays its current count', async () => {
    fakeInboxApi({
      'GET /inbox/counts': { app_updates_new_count: 3, game_activity_unread_count: 2 },
    })
    renderInbox()

    expect(await screen.findByRole('tab', { name: 'App Updates, 3 new' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Game Activity, 2 unread' })).toBeInTheDocument()
  })

  it('F25-1: a row shows its source, title, subject, and time', async () => {
    const user = userEvent.setup()
    fakeInboxApi({ 'GET /inbox/game-activity': feed([gameItem()]) })
    renderInbox()
    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))

    const row = await screen.findByRole('button', { name: /Game updated/ })
    expect(within(row).getByText('[Official Game]')).toBeInTheDocument()
    expect(within(row).getByText('Evening Pickup · Sat, Jun 15, 2030 at 6 PM')).toBeInTheDocument()
    expect(within(row).getByText('June 15, 2030')).toBeInTheDocument()
  })

  it('F25-2: App Updates offers All and New and shows the results for New', async () => {
    const user = userEvent.setup()
    const newItem = inboxItem({ source_id: itemId(1), original_notification_id: itemId(1), title: 'New update' })
    fakeInboxApi((endpoint, url) => {
      if (endpoint !== 'GET /inbox/app-updates') return undefined
      return url.searchParams.get('filter') === 'new'
        ? feed([newItem])
        : feed([inboxItem({ is_new: false, read_at: '2030-06-15T18:01:00Z' }), newItem])
    })
    renderInbox()
    const filter = await screen.findByRole('combobox', { name: 'Filter App Updates' })

    expect(optionLabels(filter)).toEqual(['All updates', 'New only'])
    await screen.findByText('Account updated')
    await user.selectOptions(filter, 'new')
    await waitFor(() => expect(screen.queryByText('Account updated')).not.toBeInTheDocument())
    expect(screen.getByText('New update')).toBeInTheDocument()
  })

  it('F25-2: Game Activity offers All, Unread, and Read and shows the results for Read', async () => {
    const user = userEvent.setup()
    const readItem = gameItem({ source_id: itemId(2), title: 'Read update', is_new: false, read_at: '2030-06-15T18:01:00Z' })
    fakeInboxApi((endpoint, url) => {
      if (endpoint !== 'GET /inbox/game-activity') return undefined
      return url.searchParams.get('filter') === 'read'
        ? feed([readItem])
        : feed([gameItem(), readItem])
    })
    renderInbox()
    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
    const filter = await screen.findByRole('combobox', { name: 'Filter Game Activity' })

    expect(optionLabels(filter)).toEqual(['All activity', 'Unread only', 'Read only'])
    await screen.findByText('Game updated')
    await user.selectOptions(filter, 'read')
    await waitFor(() => expect(screen.queryByText('Game updated')).not.toBeInTheDocument())
    expect(screen.getByText('Read update')).toBeInTheDocument()
  })

  it('F25-2: each feed keeps its own filter and loaded rows when the user switches tabs', async () => {
    const user = userEvent.setup()
    fakeInboxApi((endpoint) => {
      if (endpoint === 'GET /inbox/app-updates') return feed([inboxItem()])
      if (endpoint === 'GET /inbox/game-activity') return feed([gameItem()])
      return undefined
    })
    renderInbox()
    await screen.findByText('Account updated')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter App Updates' }), 'new')
    await screen.findByText('Account updated')
    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
    await screen.findByText('Game updated')
    await user.click(screen.getByRole('tab', { name: /App Updates/ }))

    expect(screen.getByRole('combobox', { name: 'Filter App Updates' })).toHaveValue('new')
    expect(screen.getByText('Account updated')).toBeInTheDocument()
    expect(requestCount('GET /inbox/app-updates')).toBe(2)
  })

  it('F25-12: an empty feed shows its empty message, and each empty filter result names its filter', async () => {
    const user = userEvent.setup()
    fakeInboxApi()
    renderInbox()

    expect(await screen.findByText('No app updates')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter App Updates' }), 'new')
    expect(await screen.findByText('No new app updates')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
    expect(await screen.findByText('No game activity')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter Game Activity' }), 'unread')
    expect(await screen.findByText('No unread game activity')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter Game Activity' }), 'read')
    expect(await screen.findByText('No read game activity')).toBeInTheDocument()
  })
})
