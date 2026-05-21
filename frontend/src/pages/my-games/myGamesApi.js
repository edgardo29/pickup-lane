import { apiRequest } from '../../lib/apiClient.js'

export async function loadMyGamesData(userId) {
  const [games, images, participants, myParticipants] = await Promise.all([
    apiRequest('/games'),
    apiRequest('/game-images?image_status=active&is_primary=true'),
    apiRequest('/game-participants'),
    apiRequest(`/game-participants?user_id=${userId}`),
  ])

  return { games, images, myParticipants, participants }
}
