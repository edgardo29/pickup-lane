import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../../src/lib/apiClient.js'
import {
  deferred, fakeInboxApi, feed, inboxItem, isSecondAccount, itemId, renderInbox,
  setAuth, switchAccount,
} from './inboxTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()), apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => setAuth())

function update(number, title) {
  return inboxItem({ source_id: itemId(number), original_notification_id: itemId(number), title })
}

// The rows' visible text, top to bottom.
function rowTexts() {
  return screen.getAllByRole('button', { name: /\[Account\]/ }).map((row) => row.textContent)
}

function rowsInOrder(titles) {
  return titles.map((title) => expect.stringContaining(title))
}

describe('Inbox loading and recovery', () => {
  it('F25-9: Load More appends the later items in order, without duplicate rows', async () => {
    const user = userEvent.setup()
    const first = update(1, 'First update')
    const second = update(2, 'Second update')
    const third = update(3, 'Third update')
    fakeInboxApi((endpoint, url) => {
      if (endpoint !== 'GET /inbox/app-updates') return undefined
      return url.searchParams.get('cursor')
        ? feed([second, third])
        : feed([first, second], { has_more: true, next_cursor: 'cursor-2' })
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: 'Load More' }))

    await screen.findByText('Third update')
    expect(rowTexts()).toEqual(rowsInOrder(['First update', 'Second update', 'Third update']))
  })

  it('F25-9: Load More ends after the final batch', async () => {
    const user = userEvent.setup()
    fakeInboxApi((endpoint, url) => {
      if (endpoint !== 'GET /inbox/app-updates') return undefined
      return url.searchParams.get('cursor')
        ? feed([update(2, 'Second update')])
        : feed([update(1, 'First update')], { has_more: true, next_cursor: 'cursor-2' })
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: 'Load More' }))

    await screen.findByText('Second update')
    expect(screen.queryByRole('button', { name: 'Load More' })).not.toBeInTheDocument()
  })

  it('F25-10: a failed initial feed request shows the feed error', async () => {
    fakeInboxApi({
      'GET /inbox/app-updates': new ApiRequestError('Something went wrong. Please try again.', { status: 503 }),
    })
    renderInbox()

    expect(await screen.findByRole('heading', { name: 'Could not load inbox' })).toBeInTheDocument()
    expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument()
  })

  it('F25-10: a failed later batch keeps the loaded rows and offers retry', async () => {
    const user = userEvent.setup()
    let laterAttempts = 0
    fakeInboxApi((endpoint, url) => {
      if (endpoint !== 'GET /inbox/app-updates') return undefined
      if (!url.searchParams.get('cursor')) {
        return feed([update(1, 'First update')], { has_more: true, next_cursor: 'cursor-2' })
      }
      laterAttempts += 1
      return laterAttempts === 1
        ? new ApiRequestError('Something went wrong. Please try again.', { status: 503 })
        : feed([update(2, 'Second update')])
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: 'Load More' }))

    expect(await screen.findByText('Something went wrong. Please try again.')).toBeInTheDocument()
    expect(screen.getByText('First update')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Load More' }))
    expect(await screen.findByText('Second update')).toBeInTheDocument()
  })

  it("F25-11: a Load More from the old filter is ignored; only the new filter's rows appear and its Load More works", async () => {
    const user = userEvent.setup()
    const oldBatch = deferred()
    fakeInboxApi((endpoint, url) => {
      if (endpoint !== 'GET /inbox/app-updates') return undefined
      const cursor = url.searchParams.get('cursor')
      if (cursor === 'all-cursor') return oldBatch.promise
      if (cursor === 'new-cursor') return feed([update(4, 'Second new update')])
      return url.searchParams.get('filter') === 'new'
        ? feed([update(3, 'First new update')], { has_more: true, next_cursor: 'new-cursor' })
        : feed([update(1, 'First all update')], { has_more: true, next_cursor: 'all-cursor' })
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: 'Load More' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter App Updates' }), 'new')
    await screen.findByText('First new update')

    await act(async () => {
      oldBatch.resolve(feed([update(2, 'Stale all update')]))
      await oldBatch.promise
    })
    expect(screen.queryByText('Stale all update')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Load More' }))

    await screen.findByText('Second new update')
    expect(rowTexts()).toEqual(rowsInOrder(['First new update', 'Second new update']))
  })

  it('F25-15: after an account switch during Load More, the old batch is ignored and the new feed loads and paginates', async () => {
    const user = userEvent.setup()
    const oldBatch = deferred()
    fakeInboxApi((endpoint, url, options) => {
      if (endpoint !== 'GET /inbox/app-updates') return undefined
      const cursor = url.searchParams.get('cursor')
      if (cursor === 'first-account-cursor') return oldBatch.promise
      if (cursor === 'second-account-cursor') return feed([update(4, 'Second account later update')])
      return isSecondAccount(options)
        ? feed([update(3, 'Second account update')], { has_more: true, next_cursor: 'second-account-cursor' })
        : feed([update(1, 'First account update')], { has_more: true, next_cursor: 'first-account-cursor' })
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: 'Load More' }))
    switchAccount()
    await screen.findByText('Second account update')

    await act(async () => {
      oldBatch.resolve(feed([update(2, 'First account stale update')]))
      await oldBatch.promise
    })
    expect(screen.queryByText('First account update')).not.toBeInTheDocument()
    expect(screen.queryByText('First account stale update')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Load More' }))

    await waitFor(() => {
      expect(rowTexts()).toEqual(rowsInOrder(['Second account update', 'Second account later update']))
    })
  })
})
