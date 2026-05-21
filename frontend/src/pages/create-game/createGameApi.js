import { apiRequest } from '../../lib/apiClient.js'

export async function postJson(path, payload) {
  return apiRequest(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function patchJson(path, payload) {
  return apiRequest(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function publishCommunityGame(payload) {
  const response = await postJson('/community-games/publish', payload)
  return response.game
}

export async function loadEditableGame(gameId) {
  const game = await apiRequest(`/games/${gameId}`)
  const venue = await apiRequest(`/venues/${game.venue_id}`).catch(() => null)
  const communityDetails = await apiRequest(`/community-game-details?game_id=${gameId}`)
    .then((details) => details[0] || null)
    .catch(() => null)
  return { communityDetails, game, venue }
}

export async function loadHostPublishFees(userId) {
  return apiRequest(`/host-publish-fees?host_user_id=${userId}`).catch(() => [])
}

export async function loadUserPaymentMethods(userId) {
  return apiRequest(`/user-payment-methods?user_id=${userId}`)
}
