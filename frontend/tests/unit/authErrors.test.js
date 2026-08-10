import assert from 'node:assert/strict'
import { test } from 'node:test'

import { getAuthErrorMessage } from '../../src/lib/authErrors.js'

test('sign-in credential mismatch errors use one public message', () => {
  const expected = 'Email or password is incorrect.'

  assert.equal(getAuthErrorMessage({ code: 'auth/invalid-credential' }), expected)
  assert.equal(getAuthErrorMessage({ code: 'auth/wrong-password' }), expected)
  assert.equal(getAuthErrorMessage({ code: 'auth/user-not-found' }), expected)
})

test('non-sign-in auth errors keep their specific public messages', () => {
  assert.equal(
    getAuthErrorMessage({ code: 'auth/email-already-in-use' }),
    'An account already exists with this email.',
  )
  assert.equal(
    getAuthErrorMessage({ code: 'auth/network-request-failed' }),
    'Network issue. Check your connection and try again.',
  )
})
