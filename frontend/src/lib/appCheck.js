import {
  ReCaptchaEnterpriseProvider,
  getToken,
  initializeAppCheck,
} from 'firebase/app-check'

export const APP_CHECK_HEADER_NAME = 'X-Firebase-AppCheck'

const viteEnv = import.meta.env ?? {}
const ENABLED_MODES = new Set(['observe', 'enforced'])

const defaultDependencies = {
  ReCaptchaEnterpriseProvider,
  getToken,
  initializeAppCheck,
  loadFirebaseApp: async () => import('./firebase.js'),
}

let dependencies = defaultDependencies
let appCheckInstance = null
let initializationPromise = null
let configOverride = null

export async function getAppCheckToken() {
  if (!appCheckConfigured()) {
    return null
  }

  const appCheck = await getAppCheckInstance()
  if (!appCheck) {
    return null
  }

  try {
    const tokenResult = await dependencies.getToken(appCheck, false)
    return typeof tokenResult?.token === 'string' && tokenResult.token
      ? tokenResult.token
      : null
  } catch {
    return null
  }
}

export function appCheckConfigured() {
  return (
    ENABLED_MODES.has(normalizeMode(currentConfig().VITE_FIREBASE_APP_CHECK_MODE)) &&
    Boolean(
      normalizeText(
        currentConfig().VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY,
      ),
    )
  )
}

export function __resetAppCheckForTests() {
  dependencies = defaultDependencies
  appCheckInstance = null
  initializationPromise = null
  configOverride = null
}

export function __setAppCheckTestHooks({ env = null, ...nextDependencies } = {}) {
  dependencies = {
    ...defaultDependencies,
    ...nextDependencies,
  }
  appCheckInstance = null
  initializationPromise = null
  configOverride = env
}

async function getAppCheckInstance() {
  if (appCheckInstance) {
    return appCheckInstance
  }

  if (!initializationPromise) {
    initializationPromise = initializeConfiguredAppCheck()
  }

  appCheckInstance = await initializationPromise
  return appCheckInstance
}

async function initializeConfiguredAppCheck() {
  try {
    const siteKey = normalizeText(
      currentConfig().VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY,
    )
    const { app } = await dependencies.loadFirebaseApp()
    return dependencies.initializeAppCheck(app, {
      provider: new dependencies.ReCaptchaEnterpriseProvider(siteKey),
      isTokenAutoRefreshEnabled: true,
    })
  } catch {
    return null
  }
}

function currentConfig() {
  return configOverride || viteEnv
}

function normalizeMode(value) {
  return normalizeText(value).toLowerCase()
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}
