import assert from 'node:assert/strict'
import { test } from 'node:test'
import { uploadAdminVenueImagesSequentially } from '../../src/pages/admin/official-games/shared/adminOfficialGamesApi.js'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, reject, resolve }
}

test('selected venue images upload and complete sequentially in selection order', async () => {
  const first = deferred()
  const calls = []
  const photos = [{ file: { name: 'first.jpg' } }, { file: { name: 'second.jpg' } }]
  const uploadImage = async (input) => {
    calls.push(input)
    if (calls.length === 1) {
      await first.promise
    }
  }

  const workflow = uploadAdminVenueImagesSequentially({
    firebaseUser: 'admin',
    photos,
    uploadImage,
    venueId: 'venue-1',
  })
  await Promise.resolve()
  assert.equal(calls.length, 1)

  first.resolve()
  await workflow
  assert.deepEqual(calls, [
    {
      file: photos[0].file,
      firebaseUser: 'admin',
      isPrimary: true,
      sortOrder: 0,
      venueId: 'venue-1',
    },
    {
      file: photos[1].file,
      firebaseUser: 'admin',
      isPrimary: false,
      sortOrder: 1,
      venueId: 'venue-1',
    },
  ])
})

test('a failed venue image stops later uploads without retrying', async () => {
  const calls = []
  const failure = new Error('synthetic upload failure')
  const uploadImage = async ({ file }) => {
    calls.push(file.name)
    throw failure
  }

  await assert.rejects(
    uploadAdminVenueImagesSequentially({
      firebaseUser: 'admin',
      photos: [{ file: { name: 'first.jpg' } }, { file: { name: 'second.jpg' } }],
      uploadImage,
      venueId: 'venue-1',
    }),
    failure,
  )
  assert.deepEqual(calls, ['first.jpg'])
})
