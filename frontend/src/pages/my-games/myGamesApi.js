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
  limit = 40,
  view = 'upcoming',
} = {}) {
  const authHeaders = await getAuthHeaders(firebaseUser)
  const params = new URLSearchParams({
    view,
    limit: String(limit),
  })

  if (cursor) {
    params.set('cursor', cursor)
  }

  return apiRequest(`/my-games?${params.toString()}`, { headers: authHeaders })
}
