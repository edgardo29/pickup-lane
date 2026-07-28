import { apiRequest } from '../../lib/apiClient.js'

export async function fetchUnreadNotificationCount(firebaseUser) {
  if (!firebaseUser) {
    return 0
  }

  const counts = await apiRequest(
    '/inbox/counts',
    {
      headers: {
        Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      },
    },
  )

  return (
    Number(counts?.app_updates_new_count || 0) +
    Number(counts?.game_activity_unread_count || 0)
  )
}
