import { apiRequest } from '../../lib/apiClient.js'

async function getAuthHeaders(firebaseUser) {
  if (!firebaseUser) {
    throw new Error('Sign in to view your games.')
  }

  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
  }
}

export async function loadMyGamesPage(firebaseUser, {
  cursor = '',
  domain = 'games',
  limit = 40,
  view = 'upcoming',
} = {}) {
  const authHeaders = await getAuthHeaders(firebaseUser)
  const endpoint = domain === 'need-a-sub' ? '/my-games/need-a-sub' : '/my-games'
  const params = new URLSearchParams({
    view,
    limit: String(limit),
  })

  if (cursor) {
    params.set('cursor', cursor)
  }

  return apiRequest(`${endpoint}?${params.toString()}`, { headers: authHeaders })
}
