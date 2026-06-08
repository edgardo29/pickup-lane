import { apiRequest } from '../../lib/apiClient.js'

export async function fetchUnreadNotificationCount(firebaseUser) {
  if (!firebaseUser) {
    return 0
  }

  const unreadNotifications = await apiRequest(
    '/notifications/me?is_read=false',
    {
      headers: {
        Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      },
    },
  )

  return unreadNotifications.length
}
