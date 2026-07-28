import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  APP_UPDATES_TAB,
  GAME_ACTIVITY_TAB,
  READ_BEHAVIOR_GLOBAL_SEEN,
  READ_BEHAVIOR_ITEM_READ,
  getInboxItemKey,
  getRenderableNotificationAction,
  getStatusFilterOptions,
  isInboxItemNew,
  shouldMarkInboxItemReadOptimistically,
} from '../../src/pages/inbox/inboxData.js'

test('getRenderableNotificationAction returns active actions with paths', () => {
  const action = {
    disabled: false,
    label: 'Open chat',
    path: '/need-a-sub/posts/post-1',
  }

  assert.equal(getRenderableNotificationAction({ action }), action)
})

test('getRenderableNotificationAction keeps disabled actions with reasons', () => {
  const action = {
    disabled: true,
    disabled_reason: 'This Need a Sub chat is closed.',
    label: 'Open chat',
    path: null,
  }

  assert.equal(getRenderableNotificationAction({ action }), action)
})

test('getRenderableNotificationAction hides broken pathless actions', () => {
  assert.equal(
    getRenderableNotificationAction({
      action: {
        disabled: false,
        label: 'Open chat',
        path: null,
      },
    }),
    null,
  )
})

test('getInboxItemKey uses source identity', () => {
  assert.equal(
    getInboxItemKey({ source_id: 'notice-1', source_type: 'platform_notice_global' }),
    'platform_notice_global:notice-1',
  )
})

test('getStatusFilterOptions returns tab-specific filters', () => {
  assert.deepEqual(
    getStatusFilterOptions(APP_UPDATES_TAB).map((option) => option.key),
    ['all', 'new'],
  )
  assert.deepEqual(
    getStatusFilterOptions(GAME_ACTIVITY_TAB).map((option) => option.key),
    ['all', 'unread', 'read'],
  )
})

test('isInboxItemNew prefers explicit is_new over legacy read state', () => {
  assert.equal(isInboxItemNew({ is_new: false, is_read: false }), false)
  assert.equal(isInboxItemNew({ is_read: false }), true)
})

test('shouldMarkInboxItemReadOptimistically skips global seen marker items', () => {
  assert.equal(
    shouldMarkInboxItemReadOptimistically({
      is_new: true,
      read_behavior: READ_BEHAVIOR_GLOBAL_SEEN,
    }),
    false,
  )
  assert.equal(
    shouldMarkInboxItemReadOptimistically({
      is_new: true,
      read_behavior: READ_BEHAVIOR_ITEM_READ,
    }),
    true,
  )
  assert.equal(
    shouldMarkInboxItemReadOptimistically({
      is_new: false,
      read_behavior: READ_BEHAVIOR_ITEM_READ,
    }),
    false,
  )
})
