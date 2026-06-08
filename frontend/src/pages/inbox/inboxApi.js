import { apiRequest } from '../../lib/apiClient.js'

export async function loadInboxData(firebaseUser) {
  const authHeaders = await getInboxAuthHeaders(firebaseUser)
  const notifications = await apiRequest('/notifications/me', { headers: authHeaders })

  return { notifications }
}

export async function saveNotificationRead(firebaseUser, notificationId) {
  return apiRequest(`/notifications/${notificationId}/read`, {
    method: 'PATCH',
    headers: await getInboxAuthHeaders(firebaseUser),
  })
}

async function getInboxAuthHeaders(firebaseUser) {
  if (!firebaseUser) {
    throw new Error('Sign in to view your inbox.')
  }

  return {
    Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
  }
}
