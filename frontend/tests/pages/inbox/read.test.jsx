import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError, apiRequest } from '../../../src/lib/apiClient.js'
import {
  ITEM_ID, deferred, fakeInboxApi, feed, gameItem, inboxItem, isSecondAccount, itemId,
  notificationRead, renderInbox, requestCount, setAuth, switchAccount,
} from './inboxTestKit.jsx'

vi.mock('../../../src/lib/apiClient.js', async (importOriginal) => ({
  ...(await importOriginal()), apiRequest: vi.fn(),
}))
vi.mock('../../../src/hooks/useAuth.js', () => ({ useAuth: vi.fn() }))
vi.mock('../../../src/components/app/AppNav.jsx', () => ({ default: () => null }))

beforeEach(() => setAuth())

const READ_ENDPOINT = 'PATCH /notifications/{notification_id}/read'
const SELECTED_READ_ENDPOINT = 'PUT /inbox/app-updates/platform-notices/{notice_id}/read'
const GLOBAL_SEEN_ENDPOINT = 'PUT /inbox/app-updates/global-seen'
const SAVE_FAILED = new ApiRequestError('Something went wrong. Please try again.', { status: 503 })

function appTab() {
  return screen.getByRole('tab', { name: /App Updates/ })
}

function gameTab() {
  return screen.getByRole('tab', { name: /Game Activity/ })
}

function globalNotice(overrides = {}) {
  return inboxItem({
    source_type: 'platform_notice_global',
    source_id: itemId(30),
    item_kind: 'platform_notice',
    title: 'Fields reopen Saturday',
    message: 'All fields reopen Saturday morning.',
    source_label: 'Pickup Lane',
    subject_label: 'Pickup Lane',
    row_subject: '',
    summary: 'All fields reopen Saturday morning.',
    read_behavior: 'global_seen_marker',
    icon: 'Megaphone',
    severity: 'default',
    notification_type: null,
    notification_domain: 'app',
    original_notification_id: null,
    ...overrides,
  })
}

function selectedNotice() {
  return inboxItem({
    source_type: 'platform_notice_selected',
    source_id: itemId(31),
    item_kind: 'platform_notice',
    title: 'Your league update',
    message: 'Your league schedule is posted.',
    source_label: 'Pickup Lane',
    subject_label: 'Pickup Lane',
    row_subject: '',
    summary: 'Your league schedule is posted.',
    icon: 'Megaphone',
    severity: 'default',
    notification_type: null,
    notification_domain: 'app',
    original_notification_id: null,
  })
}

describe('Inbox read state', () => {
  it('F25-3: opening an unread row opens its detail modal with the full text', async () => {
    const user = userEvent.setup()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([inboxItem()]),
      [READ_ENDPOINT]: deferred().promise,
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByRole('heading', { name: 'Account updated' })).toBeInTheDocument()
    expect(within(dialog).getByText('Your account settings were updated.')).toBeInTheDocument()
  })

  it('F25-3: opening an unread row saves its read state and lowers the count', async () => {
    const user = userEvent.setup()
    const item = inboxItem()
    fakeInboxApi({
      'GET /inbox/counts': { app_updates_new_count: 1, game_activity_unread_count: 0 },
      'GET /inbox/app-updates': feed([item]),
      [READ_ENDPOINT]: notificationRead(item),
    })
    renderInbox()
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates1'))
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))

    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(`/notifications/${ITEM_ID}/read`, expect.anything())
    expect(appTab()).toHaveTextContent('App Updates0')
  })

  it('F25-3: under New, the opened row leaves the list', async () => {
    const user = userEvent.setup()
    const item = inboxItem()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([item]),
      [READ_ENDPOINT]: notificationRead(item),
    })
    renderInbox()
    await screen.findByText('Account updated')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter App Updates' }), 'new')
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))
    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    await user.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.queryByRole('button', { name: /Account updated/ })).not.toBeInTheDocument()
    expect(screen.getByText('No new app updates')).toBeInTheDocument()
  })

  it('F25-3: under All, the opened row stays and shows as read', async () => {
    const user = userEvent.setup()
    const item = inboxItem()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([item]),
      [READ_ENDPOINT]: notificationRead(item),
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))
    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    await user.click(screen.getByRole('button', { name: 'Back' }))

    const row = screen.getByRole('button', { name: /Account updated/ })
    expect(within(row).queryByText('New')).not.toBeInTheDocument()
  })

  it('F25-3: opening an unread Game Activity row saves its read state and lowers its count', async () => {
    const user = userEvent.setup()
    const item = gameItem()
    fakeInboxApi({
      'GET /inbox/counts': { app_updates_new_count: 0, game_activity_unread_count: 1 },
      'GET /inbox/game-activity': feed([item]),
      [READ_ENDPOINT]: notificationRead(item),
    })
    renderInbox()
    await waitFor(() => expect(gameTab()).toHaveTextContent('Game Activity1'))
    await user.click(gameTab())
    await user.click(await screen.findByRole('button', { name: /Game updated/ }))

    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(`/notifications/${item.source_id}/read`, expect.anything())
    expect(gameTab()).toHaveTextContent('Game Activity0')
  })

  it('F25-3: under Unread, the opened Game Activity row leaves the list', async () => {
    const user = userEvent.setup()
    const item = gameItem()
    fakeInboxApi({
      'GET /inbox/game-activity': feed([item]),
      [READ_ENDPOINT]: notificationRead(item),
    })
    renderInbox()
    await user.click(gameTab())
    await screen.findByText('Game updated')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter Game Activity' }), 'unread')
    await user.click(await screen.findByRole('button', { name: /Game updated/ }))
    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    await user.click(screen.getByRole('button', { name: 'Back' }))

    expect(screen.queryByRole('button', { name: /Game updated/ })).not.toBeInTheDocument()
    expect(screen.getByText('No unread game activity')).toBeInTheDocument()
  })

  it('F25-3: a read save that finishes after a switch to New removes the row from the New list', async () => {
    const user = userEvent.setup()
    const item = inboxItem()
    const readSave = deferred()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([item]),
      [READ_ENDPOINT]: readSave.promise,
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))
    await user.click(screen.getByRole('button', { name: 'Back' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter App Updates' }), 'new')
    await waitFor(() => expect(requestCount('GET /inbox/app-updates')).toBe(2))
    expect(await screen.findByRole('button', { name: /Account updated/ })).toBeInTheDocument()

    await act(async () => {
      readSave.resolve(notificationRead(item))
      await readSave.promise
    })

    expect(screen.queryByRole('button', { name: /Account updated/ })).not.toBeInTheDocument()
    expect(screen.getByText('No new app updates')).toBeInTheDocument()
  })

  it('F25-3: opening a selected platform notice saves its item read state', async () => {
    const user = userEvent.setup()
    const notice = selectedNotice()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([notice]),
      [SELECTED_READ_ENDPOINT]: { ...notice, is_new: false, read_at: '2030-06-15T18:01:00Z' },
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: /Your league update/ }))

    await waitFor(() => expect(requestCount(SELECTED_READ_ENDPOINT)).toBe(1))
    expect(vi.mocked(apiRequest)).toHaveBeenCalledWith(
      `/inbox/app-updates/platform-notices/${notice.source_id}/read`,
      expect.objectContaining({ method: 'PUT' }),
    )
  })

  it('F25-4: viewing App Updates with a new global notice saves the seen marker and clears the count', async () => {
    const seenBodies = []
    const seenSave = deferred()
    fakeInboxApi((endpoint, url, options) => {
      if (endpoint === 'GET /inbox/counts') return { app_updates_new_count: 1, game_activity_unread_count: 0 }
      if (endpoint === 'GET /inbox/app-updates') return feed([globalNotice()], { global_seen_token: 'seen-token-1' })
      if (endpoint === GLOBAL_SEEN_ENDPOINT) {
        seenBodies.push(JSON.parse(options.body))
        return seenSave.promise
      }
      return undefined
    })
    renderInbox()

    await waitFor(() => expect(seenBodies).toEqual([{ seen_token: 'seen-token-1' }]))
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates1'))
    await act(async () => {
      seenSave.resolve({ app_updates_new_count: 0, game_activity_unread_count: 0 })
      await seenSave.promise
    })
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates0'))
  })

  it('F25-4: opening a global notice sends no item read', async () => {
    const user = userEvent.setup()
    fakeInboxApi({
      'GET /inbox/app-updates': feed([globalNotice()]),
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: /Fields reopen Saturday/ }))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(requestCount(READ_ENDPOINT)).toBe(0)
    expect(requestCount(SELECTED_READ_ENDPOINT)).toBe(0)
  })

  it('F25-7: a failed read save restores the unread row and the count', async () => {
    const user = userEvent.setup()
    fakeInboxApi({
      'GET /inbox/counts': { app_updates_new_count: 1, game_activity_unread_count: 0 },
      'GET /inbox/app-updates': feed([inboxItem()]),
      [READ_ENDPOINT]: SAVE_FAILED,
    })
    renderInbox()
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates1'))
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))
    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    await user.click(screen.getByRole('button', { name: 'Back' }))

    expect(appTab()).toHaveTextContent('App Updates1')
    const row = screen.getByRole('button', { name: /Account updated/ })
    expect(within(row).getByText('New')).toBeInTheDocument()
  })

  it("F25-7: a read save that fails after an account switch does not change the new account's count", async () => {
    const user = userEvent.setup()
    const readSave = deferred()
    fakeInboxApi((endpoint, url, options) => {
      if (endpoint === 'GET /inbox/counts') {
        return isSecondAccount(options)
          ? { app_updates_new_count: 5, game_activity_unread_count: 0 }
          : { app_updates_new_count: 1, game_activity_unread_count: 0 }
      }
      if (endpoint === 'GET /inbox/app-updates') return feed(isSecondAccount(options) ? [] : [inboxItem()])
      if (endpoint === READ_ENDPOINT) return readSave.promise
      return undefined
    })
    renderInbox()
    await user.click(await screen.findByRole('button', { name: /Account updated/ }))
    await waitFor(() => expect(requestCount(READ_ENDPOINT)).toBe(1))
    switchAccount()
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates5'))

    await act(async () => {
      readSave.reject(SAVE_FAILED)
      await readSave.promise.catch(() => {})
    })

    expect(appTab()).toHaveTextContent('App Updates5')
  })

  it("F25-7: a read save that finishes after a filter switch does not change the new filter's list", async () => {
    const user = userEvent.setup()
    const item = inboxItem()
    const otherItem = inboxItem({ source_id: itemId(3), original_notification_id: itemId(3), title: 'Other update', is_new: false, read_at: '2030-06-15T18:01:00Z' })
    const readSave = deferred()
    fakeInboxApi((endpoint, url) => {
      if (endpoint === 'GET /inbox/app-updates') {
        return url.searchParams.get('filter') === 'new' ? feed([item]) : feed([item, otherItem])
      }
      if (endpoint === READ_ENDPOINT) return readSave.promise
      return undefined
    })
    renderInbox()
    const filter = await screen.findByRole('combobox', { name: 'Filter App Updates' })
    await screen.findByText('Other update')
    await user.selectOptions(filter, 'new')
    await waitFor(() => expect(screen.queryByText('Other update')).not.toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /Account updated/ }))
    await user.click(screen.getByRole('button', { name: 'Back' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter App Updates' }), 'all')
    await screen.findByText('Other update')

    await act(async () => {
      readSave.resolve(notificationRead(item))
      await readSave.promise
    })

    expect(screen.getByRole('button', { name: /Account updated/ })).toBeInTheDocument()
  })

  it('F25-8: a failed global seen save keeps the notice new, and a later App Updates view retries', async () => {
    const user = userEvent.setup()
    let seenAttempts = 0
    fakeInboxApi((endpoint) => {
      if (endpoint === 'GET /inbox/counts') return { app_updates_new_count: 1, game_activity_unread_count: 0 }
      if (endpoint === 'GET /inbox/app-updates') return feed([globalNotice()], { global_seen_token: 'seen-token-1' })
      if (endpoint === GLOBAL_SEEN_ENDPOINT) {
        seenAttempts += 1
        return seenAttempts === 1 ? SAVE_FAILED : { app_updates_new_count: 0, game_activity_unread_count: 0 }
      }
      return undefined
    })
    renderInbox()
    await waitFor(() => expect(requestCount(GLOBAL_SEEN_ENDPOINT)).toBe(1))
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates1'))
    const row = screen.getByRole('button', { name: /Fields reopen Saturday/ })
    expect(within(row).getByText('New')).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: /Game Activity/ }))
    await user.click(appTab())

    await waitFor(() => expect(requestCount(GLOBAL_SEEN_ENDPOINT)).toBe(2))
    await waitFor(() => expect(appTab()).toHaveTextContent('App Updates0'))
  })
})
