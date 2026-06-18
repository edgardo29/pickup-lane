import { apiRequest } from '../../lib/apiClient.js'
import { listUserPaymentMethods } from '../../lib/paymentMethodsApi.js'
import { emptyGameCreditBalance, emptySettings, emptyStats } from './profileData.js'

export async function loadProfileData(firebaseUser = null) {
  const [
    userResponse,
    gameCreditBalanceResponse,
    paymentMethodsResponse,
    settingsResponse,
    statsResponse,
  ] = await Promise.all([
    loadCurrentProfileUser(firebaseUser),
    loadGameCreditBalance(firebaseUser).catch(() => emptyGameCreditBalance),
    firebaseUser ? listUserPaymentMethods(firebaseUser).catch(() => []) : Promise.resolve([]),
    authenticatedProfileRequest(firebaseUser, '/user-settings/me').catch(() => emptySettings),
    authenticatedProfileRequest(firebaseUser, '/user-stats/me').catch(() => emptyStats),
  ])

  return {
    gameCreditBalance: gameCreditBalanceResponse,
    paymentMethods: paymentMethodsResponse,
    settings: settingsResponse,
    stats: statsResponse,
    user: userResponse,
  }
}

function loadCurrentProfileUser(firebaseUser) {
  return authenticatedProfileRequest(firebaseUser, '/users/me')
}

async function loadGameCreditBalance(firebaseUser) {
  if (!firebaseUser) {
    return emptyGameCreditBalance
  }

  return apiRequest('/game-credits/balance', {
    headers: {
      Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
    },
  })
}

export function updateProfileUser(firebaseUser, profilePayload) {
  return authenticatedProfileRequest(firebaseUser, '/users/me', {
    method: 'PATCH',
    includeJson: true,
    body: JSON.stringify(profilePayload),
  })
}

export function saveUserSettings(firebaseUser, nextSettings) {
  return authenticatedProfileRequest(firebaseUser, '/user-settings/me', {
    method: 'PATCH',
    includeJson: true,
    body: JSON.stringify(nextSettings),
  })
}

async function authenticatedProfileRequest(firebaseUser, path, options = {}) {
  if (!firebaseUser) {
    throw new Error('Sign in to view your profile.')
  }

  const headers = {
    Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
    ...(options.includeJson ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  }
  const requestOptions = { ...options }
  delete requestOptions.includeJson

  return apiRequest(path, {
    ...requestOptions,
    headers,
  })
}
