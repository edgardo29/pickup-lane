import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  APP_UPDATES_TAB,
  GAME_ACTIVITY_TAB,
} from '../../src/pages/inbox/inboxData.js'
import {
  buildInboxUserChangeReset,
} from '../../src/pages/inbox/inboxState.js'

test('buildInboxUserChangeReset does nothing for the same active user', () => {
  assert.equal(
    buildInboxUserChangeReset({
      activeUserId: 'user-1',
      loadedUserId: 'user-1',
    }),
    null,
  )
})

test('buildInboxUserChangeReset clears user-scoped inbox state when active user changes', () => {
  const reset = buildInboxUserChangeReset({
    activeUserId: 'user-2',
    loadedUserId: 'user-1',
  })

  assert.equal(reset.loadedUserId, 'user-2')
  assert.equal(reset.globalSeenInFlight, '')
  assert.equal(reset.activeNotification, null)
  assert.deepEqual(reset.counts, {
    app_updates_new_count: 0,
    game_activity_unread_count: 0,
  })
  assert.deepEqual(reset.feeds[APP_UPDATES_TAB].items, [])
  assert.deepEqual(reset.feeds[GAME_ACTIVITY_TAB].items, [])
  assert.equal(reset.feeds[APP_UPDATES_TAB].status, 'idle')
  assert.equal(reset.feeds[GAME_ACTIVITY_TAB].status, 'idle')
})
