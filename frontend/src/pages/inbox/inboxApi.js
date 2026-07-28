import { apiRequest } from '../../lib/apiClient.js'

const INBOX_FEED_ENDPOINTS = {
  app: '/inbox/app-updates',
  game: '/inbox/game-activity',
}

export async function loadInboxCounts(firebaseUser) {
  const authHeaders = await getInboxAuthHeaders(firebaseUser)
  return apiRequest('/inbox/counts', { headers: authHeaders })
}

export async function loadInboxFeed(
  firebaseUser,
  {
    cursor = '',
    feedKey,
    filter = 'all',
    limit = 30,
  } = {},
) {
  const endpoint = INBOX_FEED_ENDPOINTS[feedKey]
  if (!endpoint) {
    throw new Error('Inbox feed is not supported.')
  }

  const params = new URLSearchParams()
  params.set('limit', String(limit))
  params.set('filter', filter || 'all')
  if (cursor) {
    params.set('cursor', cursor)
  }

  return apiRequest(`${endpoint}?${params.toString()}`, {
    headers: await getInboxAuthHeaders(firebaseUser),
  })
}

export async function saveNotificationRead(firebaseUser, notificationId) {
  return apiRequest(`/notifications/${notificationId}/read`, {
    method: 'PATCH',
    headers: await getInboxAuthHeaders(firebaseUser),
  })
}

export async function saveGlobalAppUpdatesSeen(firebaseUser, seenToken) {
  return apiRequest('/inbox/app-updates/global-seen', {
    method: 'PUT',
    headers: await getInboxAuthHeaders(firebaseUser),
    body: JSON.stringify({ seen_token: seenToken }),
  })
}

export async function saveSelectedPlatformNoticeRead(firebaseUser, noticeId) {
  return apiRequest(`/inbox/app-updates/platform-notices/${noticeId}/read`, {
    method: 'PUT',
    headers: await getInboxAuthHeaders(firebaseUser),
  })
}

async function getInboxAuthHeaders(firebaseUser) {
  if (!firebaseUser) {
    throw new Error('Sign in to view your inbox.')
  }

  return {
    Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
    'Content-Type': 'application/json',
  }
}
