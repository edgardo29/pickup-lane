import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  EMAIL_PASSWORD_PROVIDER_ID,
  GOOGLE_PROVIDER_ID,
  getReauthenticationProviderId,
  reauthenticateWithEmailPassword,
  reauthenticateWithGoogle,
} from '../../src/lib/reauthentication.js'

test('reauthentication provider selection supports password and Google users', () => {
  assert.equal(
    getReauthenticationProviderId({
      providerData: [{ providerId: EMAIL_PASSWORD_PROVIDER_ID }],
    }),
    EMAIL_PASSWORD_PROVIDER_ID,
  )
  assert.equal(
    getReauthenticationProviderId({
      providerData: [{ providerId: GOOGLE_PROVIDER_ID }],
    }),
    GOOGLE_PROVIDER_ID,
  )
  assert.equal(
    getReauthenticationProviderId({
      providerData: [
        { providerId: GOOGLE_PROVIDER_ID },
        { providerId: EMAIL_PASSWORD_PROVIDER_ID },
      ],
    }),
    EMAIL_PASSWORD_PROVIDER_ID,
  )
  assert.equal(getReauthenticationProviderId({ providerData: [] }), '')
})

test('email password reauth uses Firebase credential reauth then refreshes the ID token', async () => {
  const calls = []
  const credential = { providerId: EMAIL_PASSWORD_PROVIDER_ID }
  const firebaseUser = {
    email: 'user@example.com',
    getIdToken: async (forceRefresh) => {
      calls.push(['getIdToken', forceRefresh])
      return ''
    },
  }
  const enteredCredential = ['entered', 'credential'].join('-')
  const authApi = {
    EmailAuthProvider: {
      credential: (email, password) => {
        calls.push(['credential', email, password])
        return credential
      },
    },
    reauthenticateWithCredential: async (user, nextCredential) => {
      calls.push(['reauthenticateWithCredential', user === firebaseUser, nextCredential])
    },
  }

  await reauthenticateWithEmailPassword({
    authApi,
    firebaseUser,
    password: enteredCredential,
  })

  assert.deepEqual(calls, [
    ['credential', 'user@example.com', enteredCredential],
    ['reauthenticateWithCredential', true, credential],
    ['getIdToken', true],
  ])
})

test('Google reauth uses Firebase popup reauth then refreshes the ID token', async () => {
  const calls = []
  const firebaseUser = {
    getIdToken: async (forceRefresh) => {
      calls.push(['getIdToken', forceRefresh])
      return ''
    },
  }
  const googleProvider = { providerId: GOOGLE_PROVIDER_ID }
  const authApi = {
    reauthenticateWithPopup: async (user, provider) => {
      calls.push(['reauthenticateWithPopup', user === firebaseUser, provider])
    },
  }

  await reauthenticateWithGoogle({
    authApi,
    firebaseUser,
    googleProvider,
  })

  assert.deepEqual(calls, [
    ['reauthenticateWithPopup', true, googleProvider],
    ['getIdToken', true],
  ])
})

test('provider reauth failure does not refresh the ID token', async () => {
  const calls = []
  const firebaseUser = {
    getIdToken: async (forceRefresh) => {
      calls.push(['getIdToken', forceRefresh])
      return ''
    },
  }
  const authApi = {
    reauthenticateWithPopup: async () => {
      calls.push(['reauthenticateWithPopup'])
      throw Object.assign(new Error('Popup closed'), {
        code: 'auth/popup-closed-by-user',
      })
    },
  }

  await assert.rejects(
    () => reauthenticateWithGoogle({
      authApi,
      firebaseUser,
      googleProvider: { providerId: GOOGLE_PROVIDER_ID },
    }),
    /Popup closed/,
  )
  assert.deepEqual(calls, [['reauthenticateWithPopup']])
})
