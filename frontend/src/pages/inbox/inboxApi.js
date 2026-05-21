import { apiRequest } from '../../lib/apiClient.js'

export async function loadInboxData(userId) {
  const [notifications, games] = await Promise.all([
    apiRequest(`/notifications?user_id=${userId}`),
    apiRequest('/games'),
  ])

  return { games, notifications }
}

export function saveNotificationRead(notificationId) {
  return apiRequest(`/notifications/${notificationId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_read: true }),
  })
}
