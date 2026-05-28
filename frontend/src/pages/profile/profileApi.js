import { apiRequest } from '../../lib/apiClient.js'
import { listUserPaymentMethods } from '../../lib/paymentMethodsApi.js'
import { emptyGameCreditBalance, emptySettings, emptyStats } from './profileData.js'

export async function loadProfileData(userId, firebaseUser = null) {
  const [
    gameCreditBalanceResponse,
    paymentMethodsResponse,
    settingsResponse,
    statsResponse,
  ] = await Promise.all([
    loadGameCreditBalance(firebaseUser).catch(() => emptyGameCreditBalance),
    firebaseUser ? listUserPaymentMethods(firebaseUser).catch(() => []) : Promise.resolve([]),
    apiRequest(`/user-settings/${userId}`).catch(() => emptySettings),
    apiRequest(`/user-stats/${userId}`).catch(() => emptyStats),
  ])

  return {
    gameCreditBalance: gameCreditBalanceResponse,
    paymentMethods: paymentMethodsResponse,
    settings: settingsResponse,
    stats: statsResponse,
  }
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

export function updateProfileUser(userId, profilePayload) {
  return apiRequest(`/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profilePayload),
  })
}

export async function saveUserSettings(userId, currentSettings, nextSettings) {
  try {
    return await apiRequest(`/user-settings/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nextSettings),
    })
  } catch (requestError) {
    if (
      requestError instanceof Error &&
      !requestError.message.toLowerCase().includes('not found')
    ) {
      throw requestError
    }

    return apiRequest('/user-settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email_notifications_enabled: currentSettings.email_notifications_enabled,
        location_permission_status: currentSettings.location_permission_status,
        marketing_opt_in: currentSettings.marketing_opt_in,
        push_notifications_enabled: currentSettings.push_notifications_enabled,
        sms_notifications_enabled: currentSettings.sms_notifications_enabled,
        user_id: userId,
        ...nextSettings,
      }),
    })
  }
}
