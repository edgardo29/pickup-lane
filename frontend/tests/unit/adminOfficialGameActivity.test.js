import assert from 'node:assert/strict'
import test from 'node:test'

import { collectOfficialGameActivityPages } from '../../src/pages/admin/official-games/manage/adminOfficialGameActivity.js'

test('official game activity follows one cursor and never requests a third page', async () => {
  const cursors = []
  const actions = await collectOfficialGameActivityPages({
    loadPage: async (cursor) => {
      cursors.push(cursor)
      return {
        actions: Array.from({ length: 50 }, (_, index) => ({
          id: `${cursors.length}-${index}`,
        })),
        next_cursor: `cursor-${cursors.length}`,
      }
    },
  })

  assert.deepEqual(cursors, ['', 'cursor-1'])
  assert.equal(actions.length, 100)
})

test('official game activity stops after a single sufficient page', async () => {
  let calls = 0
  const actions = await collectOfficialGameActivityPages({
    loadPage: async () => {
      calls += 1
      return { actions: [{ id: 'only-action' }], next_cursor: null }
    },
  })

  assert.equal(calls, 1)
  assert.deepEqual(actions, [{ id: 'only-action' }])
})
