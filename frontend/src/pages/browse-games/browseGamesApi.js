import { apiRequest } from '../../lib/apiClient.js'

export async function loadBrowseGamesData() {
  const [games, gameImages, participants] = await Promise.all([
    apiRequest('/games'),
    apiRequest('/game-images?image_status=active&is_primary=true'),
    apiRequest('/game-participants'),
  ])

  return { gameImages, games, participants }
}
