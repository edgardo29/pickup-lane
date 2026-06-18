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

export async function loadMyGamesData(firebaseUser) {
  const authHeaders = await getAuthHeaders(firebaseUser)
  const [games, images, venueImages, participantCounts, myParticipants] = await Promise.all([
    apiRequest('/games'),
    apiRequest('/game-images?image_status=active&is_primary=true'),
    apiRequest('/venue-images').catch(() => []),
    apiRequest('/games/participant-counts'),
    apiRequest('/game-participants/me', { headers: authHeaders }),
  ])

  return { games, images, myParticipants, participantCounts, venueImages }
}
