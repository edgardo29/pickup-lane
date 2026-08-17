import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'

import { apiRequest } from '../../src/lib/apiClient.js'
import {
  APP_CHECK_HEADER_NAME,
  __resetAppCheckForTests,
  __setAppCheckTestHooks,
  appCheckConfigured,
  getAppCheckToken,
} from '../../src/lib/appCheck.js'
import { uploadVenueImageObject } from '../../src/pages/admin/official-games/shared/adminOfficialGamesApi.js'

afterEach(() => {
  __resetAppCheckForTests()
  delete globalThis.fetch
})

test('disabled or unconfigured frontend App Check returns no token', async () => {
  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'disabled',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    initializeAppCheck: () => {
      throw new Error('disabled App Check must not initialize')
    },
  })

  assert.equal(appCheckConfigured(), false)
  assert.equal(await getAppCheckToken(), null)

  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'observe',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: '',
    },
    initializeAppCheck: () => {
      throw new Error('missing site key must not initialize')
    },
  })

  assert.equal(appCheckConfigured(), false)
  assert.equal(await getAppCheckToken(), null)
})

test('configured frontend App Check lazily initializes and returns provider token', async () => {
  const calls = []
  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'observe',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    ReCaptchaEnterpriseProvider: class {
      constructor(siteKey) {
        calls.push(['provider', siteKey])
      }
    },
    loadFirebaseApp: async () => {
      calls.push(['load-app'])
      return { app: { name: 'synthetic-firebase-app' } }
    },
    initializeAppCheck: (app, options) => {
      calls.push(['initialize', app.name, options.isTokenAutoRefreshEnabled])
      return { appCheck: true }
    },
    getToken: async (appCheck, forceRefresh) => {
      calls.push(['get-token', appCheck.appCheck, forceRefresh])
      return { token: 'synthetic-app-check-token' }
    },
  })

  assert.equal(appCheckConfigured(), true)
  assert.equal(await getAppCheckToken(), 'synthetic-app-check-token')
  assert.deepEqual(calls, [
    ['load-app'],
    ['provider', 'synthetic-site-key'],
    ['initialize', 'synthetic-firebase-app', true],
    ['get-token', true, false],
  ])
})

test('initialization and acquisition failures return no token without persistence', async () => {
  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'enforced',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    loadFirebaseApp: async () => {
      throw new Error('synthetic initialization failure')
    },
  })

  assert.equal(await getAppCheckToken(), null)

  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'enforced',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    loadFirebaseApp: async () => ({ app: {} }),
    initializeAppCheck: () => ({ appCheck: true }),
    getToken: async () => {
      throw new Error('synthetic token failure')
    },
  })

  assert.equal(await getAppCheckToken(), null)
  assert.equal(globalThis.localStorage, undefined)
  assert.equal(globalThis.sessionStorage, undefined)
})

test('api client attaches App Check header only to relative Pickup Lane API requests', async () => {
  const fetchCalls = []
  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'observe',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    loadFirebaseApp: async () => ({ app: {} }),
    initializeAppCheck: () => ({ appCheck: true }),
    getToken: async () => ({ token: 'synthetic-app-check-token' }),
  })
  globalThis.fetch = async (url, options) => {
    fetchCalls.push([url, options])
    return okJson({ ok: true })
  }

  await apiRequest('/games', {
    headers: { Authorization: 'Bearer synthetic-id-token' },
  })
  await apiRequest('https://uploads.example.invalid/object')

  assert.equal(fetchCalls[0][1].headers.Authorization, 'Bearer synthetic-id-token')
  assert.equal(
    fetchCalls[0][1].headers[APP_CHECK_HEADER_NAME],
    'synthetic-app-check-token',
  )
  assert.equal(fetchCalls[1][0], 'https://uploads.example.invalid/object')
  assert.equal(fetchCalls[1][1].headers[APP_CHECK_HEADER_NAME], undefined)
})

test('direct signed provider upload keeps App Check out of provider request', async () => {
  const fetchCalls = []
  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'enforced',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    getToken: async () => ({ token: 'synthetic-app-check-token' }),
  })
  globalThis.fetch = async (url, options) => {
    fetchCalls.push([url, options])
    return {
      ok: true,
      status: 200,
      headers: {
        get: (name) => (name.toLowerCase() === 'etag' ? '"synthetic-etag"' : null),
      },
    }
  }

  const etag = await uploadVenueImageObject({
    file: new Blob(['synthetic image']),
    uploadHeaders: { 'Content-Type': 'image/webp' },
    uploadUrl: 'https://r2.example.invalid/signed-object',
  })

  assert.equal(etag, '"synthetic-etag"')
  assert.equal(fetchCalls.length, 1)
  assert.equal(fetchCalls[0][0], 'https://r2.example.invalid/signed-object')
  assert.deepEqual(fetchCalls[0][1].headers, { 'Content-Type': 'image/webp' })
})

test('api client does not retry failed App Check or API responses globally', async () => {
  let fetchCount = 0
  __setAppCheckTestHooks({
    env: {
      VITE_FIREBASE_APP_CHECK_MODE: 'observe',
      VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY: 'synthetic-site-key',
    },
    loadFirebaseApp: async () => ({ app: {} }),
    initializeAppCheck: () => ({ appCheck: true }),
    getToken: async () => {
      throw new Error('synthetic App Check acquisition failure')
    },
  })
  globalThis.fetch = async () => {
    fetchCount += 1
    return {
      ok: false,
      status: 403,
      json: async () => ({ code: 'APP_CHECK.REQUIRED', detail: 'denied' }),
    }
  }

  await assert.rejects(() => apiRequest('/games'), { code: 'APP_CHECK.REQUIRED' })
  assert.equal(fetchCount, 1)
})

function okJson(payload) {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  }
}
