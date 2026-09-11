import assert from 'node:assert/strict'
import test from 'node:test'

import {
  beginChatRevealRequest,
  invalidateChatRevealRequest,
  shouldApplyChatRevealResponse,
} from '../../src/pages/admin/shared/adminChatRevealState.js'

const context = {
  messageId: 'message-a',
  offset: 20,
  parentId: 'game-a',
  parentKind: 'official_game',
  view: 'needs_review',
  viewerId: 'admin-a',
}

test('chat reveal accepts only the current full request context', () => {
  const request = beginChatRevealRequest({ generation: 4 }, context)
  assert.equal(shouldApplyChatRevealResponse(request, request), true)

  for (const changed of [
    { messageId: 'message-b' },
    { offset: 40 },
    { parentId: 'game-b' },
    { parentKind: 'community_game' },
    { view: 'removed' },
  ]) {
    const replacement = beginChatRevealRequest(request, { ...context, ...changed })
    assert.equal(shouldApplyChatRevealResponse(replacement, request), false)
  }
})

test('chat reveal invalidation rejects late success and error after close or unmount', () => {
  const request = beginChatRevealRequest({ generation: 0 }, context)
  const invalidated = invalidateChatRevealRequest(request)
  assert.equal(invalidated.context, null)
  assert.equal(shouldApplyChatRevealResponse(invalidated, request), false)
})

test('chat reveal rejects a late response when live context changes before invalidation', () => {
  const request = beginChatRevealRequest({ generation: 0 }, context)

  for (const changed of [
    { offset: 40 },
    { parentId: 'game-b' },
    { parentKind: 'community_game' },
    { view: 'removed' },
    { viewerId: 'admin-b' },
  ]) {
    assert.equal(
      shouldApplyChatRevealResponse(request, request, { ...context, ...changed }),
      false,
    )
  }
})
