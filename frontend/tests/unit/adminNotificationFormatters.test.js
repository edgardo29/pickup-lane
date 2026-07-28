import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  beginAdminNotificationRequest,
  buildAdminNotificationClearedCollectionState,
  buildAdminNotificationClearedDetailState,
  buildAdminNotificationCollectionFilters,
  cancelAdminNotificationRequest,
  formatAdminNotificationActionState,
  getAdminNotificationPrimaryReference,
  getAdminNotificationRelatedEntries,
  shouldApplyAdminNotificationResponse,
} from '../../src/pages/admin/notifications/adminNotificationFormatters.js'

test('buildAdminNotificationCollectionFilters builds recipient anchored filters', () => {
  const filters = buildAdminNotificationCollectionFilters({
    selectedRecipientId: ' user-1 ',
  })

  assert.deepEqual(filters, {
    user_id: 'user-1',
  })
})

test('admin notification related helpers use serialized related records', () => {
  const primary = {
    display_label: 'Need a Sub post',
    id: 'post-1',
    type: 'need_a_sub_post',
  }
  const related = [
    primary,
    {
      display_label: 'Need a Sub request',
      id: 'request-1',
      type: 'need_a_sub_request',
    },
  ]

  assert.deepEqual(getAdminNotificationRelatedEntries({ related_records: related }), related)
  assert.deepEqual(getAdminNotificationRelatedEntries({ related_records: null }), [])
  assert.deepEqual(getAdminNotificationPrimaryReference({ related_records: related }), primary)
  assert.deepEqual(
    getAdminNotificationPrimaryReference({
      primary_related_record: {
        display_label: 'Primary',
        id: 'primary-1',
        type: 'game',
      },
      related_records: related,
    }),
    {
      display_label: 'Primary',
      id: 'primary-1',
      type: 'game',
    },
  )
})

test('formatAdminNotificationActionState labels compact list action state', () => {
  assert.equal(
    formatAdminNotificationActionState({
      action_key: 'view_game',
      status: 'not_evaluated',
    }),
    'Stored Action',
  )
})

test('shouldApplyAdminNotificationResponse rejects stale or aborted requests', () => {
  assert.equal(
    shouldApplyAdminNotificationResponse({
      activeRequestId: 7,
      requestId: 7,
      signal: { aborted: false },
    }),
    true,
  )
  assert.equal(
    shouldApplyAdminNotificationResponse({
      activeRequestId: 8,
      requestId: 7,
      signal: { aborted: false },
    }),
    false,
  )
  assert.equal(
    shouldApplyAdminNotificationResponse({
      activeRequestId: 7,
      requestId: 7,
      signal: { aborted: true },
    }),
    false,
  )
})

test('beginAdminNotificationRequest aborts stale requests and advances ids', () => {
  const requestRef = { current: { controller: null, id: 0 } }
  const first = beginAdminNotificationRequest(requestRef)

  assert.equal(first.requestId, 1)
  assert.equal(first.controller.signal.aborted, false)
  assert.equal(requestRef.current.id, 1)

  const second = beginAdminNotificationRequest(requestRef)

  assert.equal(first.controller.signal.aborted, true)
  assert.equal(second.requestId, 2)
  assert.equal(second.controller.signal.aborted, false)
  assert.equal(requestRef.current.id, 2)
  assert.equal(
    shouldApplyAdminNotificationResponse({
      activeRequestId: requestRef.current.id,
      requestId: first.requestId,
      signal: first.controller.signal,
    }),
    false,
  )
  assert.equal(
    shouldApplyAdminNotificationResponse({
      activeRequestId: requestRef.current.id,
      requestId: second.requestId,
      signal: second.controller.signal,
    }),
    true,
  )
})

test('cancelAdminNotificationRequest aborts active requests and invalidates responses', () => {
  const requestRef = { current: { controller: null, id: 0 } }
  const active = beginAdminNotificationRequest(requestRef)

  cancelAdminNotificationRequest(requestRef)

  assert.equal(active.controller.signal.aborted, true)
  assert.deepEqual(requestRef.current, {
    controller: null,
    id: 2,
  })
  assert.equal(
    shouldApplyAdminNotificationResponse({
      activeRequestId: requestRef.current.id,
      requestId: active.requestId,
      signal: active.controller.signal,
    }),
    false,
  )
})

test('buildAdminNotificationClearedDetailState clears selected detail only', () => {
  assert.deepEqual(buildAdminNotificationClearedDetailState(), {
    detailError: '',
    detailLoadState: 'idle',
    selectedNotification: null,
    selectedNotificationId: null,
  })
})

test('buildAdminNotificationClearedCollectionState clears cursor and detail state', () => {
  assert.deepEqual(buildAdminNotificationClearedCollectionState(), {
    cursor: '',
    cursorStack: [],
    detailError: '',
    detailLoadState: 'idle',
    listError: '',
    listLoadState: 'idle',
    nextCursor: '',
    notifications: [],
    selectedNotification: null,
    selectedNotificationId: null,
  })
})
