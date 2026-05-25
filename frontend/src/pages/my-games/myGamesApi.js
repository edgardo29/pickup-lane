import { apiRequest } from '../../lib/apiClient.js'

export async function loadMyGamesData(userId) {
  const [games, images, venueImages, participants, myParticipants] = await Promise.all([
    apiRequest('/games'),
    apiRequest('/game-images?image_status=active&is_primary=true'),
    apiRequest('/venue-images').catch(() => []),
    apiRequest('/game-participants'),
    apiRequest(`/game-participants?user_id=${userId}`),
  ])

  return { games, images, myParticipants, participants, venueImages }
}
