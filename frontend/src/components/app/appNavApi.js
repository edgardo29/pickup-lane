import { apiRequest } from '../../lib/apiClient.js'

export async function fetchUnreadNotificationCount(userId) {
  const unreadNotifications = await apiRequest(
    `/notifications?user_id=${userId}&is_read=false`,
  )

  return unreadNotifications.length
}
