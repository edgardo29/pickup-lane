import assert from 'node:assert/strict'
import test from 'node:test'

import { canCancelAdminCommunityGame } from '../../src/pages/admin/community-games/adminCommunityEnforcementState.js'
import {
  isAdminEnforcementConflict,
  runAdminEnforcementMutation,
} from '../../src/pages/admin/shared/adminEnforcementLifecycle.js'

test('only HTTP 409 is an authoritative enforcement conflict', () => {
  assert.equal(isAdminEnforcementConflict({ status: 409 }), true)
  assert.equal(isAdminEnforcementConflict({ status: 400 }), false)
  assert.equal(isAdminEnforcementConflict({ status: 403 }), false)
  assert.equal(isAdminEnforcementConflict({ status: '409' }), false)
  assert.equal(isAdminEnforcementConflict(), false)
})

test('successful enforcement owns pending state and applies authoritative result', async () => {
  const events = []
  const authoritativeResult = { game_status: 'cancelled' }

  const outcome = await runAdminEnforcementMutation({
    execute: async () => {
      events.push('execute')
      return authoritativeResult
    },
    onError: () => events.push('error'),
    onPendingChange: (pending) => events.push(`pending:${pending}`),
    onSuccess: (result) => {
      assert.equal(result, authoritativeResult)
      events.push('success')
    },
  })

  assert.deepEqual(outcome, { outcome: 'success', result: authoritativeResult })
  assert.deepEqual(events, [
    'pending:true',
    'execute',
    'success',
    'pending:false',
  ])
})

test('409 clears stale state before requesting an authoritative reload', async () => {
  const events = []

  const outcome = await runAdminEnforcementMutation({
    clearStaleState: () => events.push('clear'),
    execute: async () => {
      events.push('execute')
      throw { status: 409 }
    },
    onError: () => events.push('error'),
    onPendingChange: (pending) => events.push(`pending:${pending}`),
    onSuccess: () => events.push('success'),
    reloadAuthoritativeState: () => events.push('reload'),
  })

  assert.deepEqual(outcome, { outcome: 'conflict' })
  assert.deepEqual(events, [
    'pending:true',
    'execute',
    'clear',
    'reload',
    'pending:false',
  ])
})

test('ordinary failure preserves local state and exposes the error', async () => {
  const events = []
  const failure = new Error('failed')

  const outcome = await runAdminEnforcementMutation({
    clearStaleState: () => events.push('clear'),
    execute: async () => {
      throw failure
    },
    onError: (error) => {
      assert.equal(error, failure)
      events.push('error')
    },
    reloadAuthoritativeState: () => events.push('reload'),
  })

  assert.deepEqual(outcome, { error: failure, outcome: 'error' })
  assert.deepEqual(events, ['error'])
})

test('Community Game cancellation is offered only before an active published game starts', () => {
  const now = new Date('2035-01-15T18:00:00Z')
  const eligible = {
    game_status: 'active',
    publish_status: 'published',
    starts_at: '2035-01-15T19:00:00Z',
  }

  assert.equal(canCancelAdminCommunityGame(eligible, now), true)
  for (const gameStatus of ['completed', 'cancelled', 'expired', 'removed']) {
    assert.equal(
      canCancelAdminCommunityGame({ ...eligible, game_status: gameStatus }, now),
      false,
    )
  }
  assert.equal(
    canCancelAdminCommunityGame({ ...eligible, publish_status: 'draft' }, now),
    false,
  )
  assert.equal(
    canCancelAdminCommunityGame(
      { ...eligible, starts_at: '2035-01-15T17:00:00Z' },
      now,
    ),
    false,
  )
})
