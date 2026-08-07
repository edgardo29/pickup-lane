import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

const source = readFileSync(
  new URL('../../src/pages/admin/official-games/shared/adminOfficialGamesApi.js', import.meta.url),
  'utf8',
)

test('official-game host removal uses the POST action route', () => {
  const functionStart = source.indexOf('export async function removeAdminOfficialGameHost')
  assert.notEqual(functionStart, -1)

  const functionEnd = source.indexOf('export async function addAdminOfficialGamePlayer')
  const functionSource = source.slice(functionStart, functionEnd)

  assert.match(functionSource, /\/host\/remove/)
  assert.match(functionSource, /method: 'POST'/)
  assert.doesNotMatch(functionSource, /method: 'DELETE'/)
})

test('official-game player removal no longer exposes a direct DELETE helper', () => {
  assert.doesNotMatch(source, /removeAdminOfficialGamePlayer/)
  assert.doesNotMatch(
    source,
    /method: 'DELETE'[\s\S]*\/participants\/\$\{participantId\}/,
  )
})
