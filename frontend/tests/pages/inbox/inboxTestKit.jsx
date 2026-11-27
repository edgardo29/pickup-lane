import { act, render } from '@testing-library/react'
import { useSyncExternalStore } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { apiRequest } from '../../../src/lib/apiClient.js'
import { useAuth } from '../../../src/hooks/useAuth.js'
import AccountSuspendedPage from '../../../src/pages/account-suspended/AccountSuspendedPage.jsx'
import InboxPage from '../../../src/pages/inbox/InboxPage.jsx'
import {
  RequireActiveAppUser,
  RequireSuspendedAppUser,
} from '../../../src/routes/RouteGuards.jsx'
import { checkBackendAnswer } from '../../backendFields.js'
import backendFields from './backend_fields.json'

export const USER_ID = '00000000-0000-4000-8000-000000000001'
export const OTHER_USER_ID = '00000000-0000-4000-8000-000000000002'
export const ITEM_ID = '00000000-0000-4000-8000-000000000010'
export const GAME_ID = '00000000-0000-4000-8000-000000000020'

let authState
const authListeners = new Set()

function subscribeToAuth(listener) {
  authListeners.add(listener)
  return () => authListeners.delete(listener)
}

// Like the real auth provider, a sign-in change re-renders every page using it.
export function setAuth(overrides = {}) {
  authState = {
    appUser: { id: USER_ID, account_status: 'active' },
    currentUser: { uid: 'firebase-user-1', getIdToken: vi.fn().mockResolvedValue('test-token') },
    isLoading: false,
    ...overrides,
  }
  vi.mocked(useAuth).mockImplementation(
    () => useSyncExternalStore(subscribeToAuth, () => authState),
  )
  act(() => authListeners.forEach((listener) => listener()))
  return authState
}

function endpointFor(path, method = 'GET') {
  const url = new URL(path, 'http://test.local')
  const pathname = url.pathname
  if (/^\/inbox\/app-updates\/platform-notices\/[^/]+\/read$/.test(pathname)) {
    return `${method} /inbox/app-updates/platform-notices/{notice_id}/read`
  }
  if (/^\/notifications\/[^/]+\/read$/.test(pathname)) {
    return `${method} /notifications/{notification_id}/read`
  }
  return `${method} ${pathname}`
}

afterEach(() => {
  const mockedRequest = vi.mocked(apiRequest)
  mockedRequest.mock.calls.forEach(([path, options], index) => {
    const result = mockedRequest.mock.settledResults[index]
    if (result?.type === 'fulfilled') {
      checkBackendAnswer(
        backendFields,
        endpointFor(path, options?.method || 'GET'),
        result.value,
      )
    }
  })
})

export function inboxItem(overrides = {}) {
  return {
    source_type: 'notification',
    source_id: ITEM_ID,
    item_kind: 'account_security',
    title: 'Account updated',
    message: 'Your account settings were updated.',
    source_label: 'Account',
    subject_label: 'Your account',
    subject_starts_at: null,
    subject_ends_at: null,
    subject_timezone: null,
    row_subject: 'Your account',
    summary: 'Your account settings were updated.',
    occurred_at: '2030-06-15T18:00:00Z',
    is_new: true,
    read_behavior: 'item_read',
    read_at: null,
    action: null,
    icon: 'ShieldCheck',
    severity: 'warning',
    notification_type: 'account_security',
    notification_category: 'app',
    notification_domain: 'account',
    original_notification_id: ITEM_ID,
    ...overrides,
  }
}

export function feed(items = [], overrides = {}) {
  return {
    items,
    limit: 30,
    next_cursor: null,
    has_more: false,
    global_seen_token: null,
    ...overrides,
  }
}

export function notificationRead(item = inboxItem(), overrides = {}) {
  return {
    id: item.original_notification_id,
    user_id: USER_ID,
    notification_type: item.notification_type,
    notification_category: item.notification_category,
    notification_domain: item.notification_domain,
    source_type: item.notification_domain === 'game' ? 'official_game' : 'account',
    source_label: item.source_label,
    title: item.title,
    subject_label: item.subject_label,
    subject_starts_at: item.subject_starts_at,
    subject_ends_at: item.subject_ends_at,
    subject_timezone: item.subject_timezone,
    row_subject: item.row_subject,
    summary: item.summary,
    body: item.message,
    action_key: item.action?.key || null,
    action: item.action,
    icon: item.icon,
    severity: item.severity,
    event_at: item.occurred_at,
    aggregation_key: null,
    aggregate_count: null,
    actor_user_id: null,
    related_game_id: item.notification_domain === 'game' ? GAME_ID : null,
    related_chat_id: null,
    related_booking_id: null,
    related_payment_id: null,
    related_refund_id: null,
    related_participant_id: null,
    related_message_id: null,
    related_sub_post_id: null,
    related_sub_post_chat_id: null,
    related_sub_post_chat_message_id: null,
    related_sub_post_request_id: null,
    related_sub_post_position_id: null,
    is_read: true,
    read_at: '2030-06-15T18:01:00Z',
    created_at: item.occurred_at,
    updated_at: '2030-06-15T18:01:00Z',
    ...overrides,
  }
}

export function fakeInboxApi(resolver = {}) {
  vi.mocked(apiRequest).mockImplementation((path, options = {}) => {
    const endpoint = endpointFor(path, options.method || 'GET')
    const answer = typeof resolver === 'function'
      ? resolver(endpoint, new URL(path, 'http://test.local'), options)
      : resolver[endpoint]
    const fallback = {
      'GET /inbox/counts': { app_updates_new_count: 0, game_activity_unread_count: 0 },
      'GET /inbox/app-updates': feed(),
      'GET /inbox/game-activity': feed(),
    }[endpoint]
    const result = answer === undefined ? fallback : answer
    if (result instanceof Error) return Promise.reject(result)
    if (result?.then) return result
    if (result === undefined) throw new Error(`No fake answer for ${endpoint}`)
    return Promise.resolve(result)
  })
}

export function requestCount(endpoint) {
  return vi.mocked(apiRequest).mock.calls.filter(
    ([path, options]) => endpointFor(path, options?.method || 'GET') === endpoint,
  ).length
}

export function deferred() {
  let resolve
  let reject
  const promise = new Promise((onResolve, onReject) => {
    resolve = onResolve
    reject = onReject
  })
  return { promise, reject, resolve }
}

// Item IDs are UUIDs, as the backend sends them: itemId(1) is
// 00000000-0000-4000-8000-000000000101.
export function itemId(number) {
  return `00000000-0000-4000-8000-${String(100 + number).padStart(12, '0')}`
}

export function gameItem(overrides = {}) {
  const id = overrides.source_id || itemId(50)
  return inboxItem({
    source_id: id,
    original_notification_id: id,
    item_kind: 'game_updated',
    title: 'Game updated',
    message: 'The start time changed. Review the latest game details.',
    source_label: 'Official Game',
    subject_label: 'Evening Pickup',
    subject_starts_at: '2030-06-15T23:00:00Z',
    subject_ends_at: '2030-06-16T00:00:00Z',
    subject_timezone: 'America/Chicago',
    row_subject: 'Evening Pickup · Sat, Jun 15, 2030 at 6 PM',
    summary: 'The start time changed.',
    icon: 'CalendarDays',
    severity: 'default',
    notification_type: 'game_updated',
    notification_category: 'game_activity',
    notification_domain: 'game',
    ...overrides,
  })
}

export function secondAccount() {
  return {
    appUser: { id: OTHER_USER_ID, account_status: 'active' },
    currentUser: { uid: 'firebase-user-2', getIdToken: vi.fn().mockResolvedValue('second-token') },
  }
}

export function isSecondAccount(options) {
  return options.headers?.Authorization === 'Bearer second-token'
}

// Signs a different account in, as the auth provider does.
export function switchAccount(account = secondAccount()) {
  setAuth(account)
}

export function renderInbox(initialPath = '/inbox') {
  const router = createMemoryRouter([
    {
      path: '/inbox',
      element: <RequireActiveAppUser><InboxPage /></RequireActiveAppUser>,
    },
    {
      path: '/account-suspended',
      element: <RequireSuspendedAppUser><AccountSuspendedPage /></RequireSuspendedAppUser>,
    },
    { path: '/sign-in', element: <h1>Sign In</h1> },
    { path: '/games/:gameId', element: <h1>Game Details</h1> },
  ], { initialEntries: [initialPath] })
  const result = render(<RouterProvider router={router} />)
  return { ...result, router }
}
