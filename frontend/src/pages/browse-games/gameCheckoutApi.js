import { apiRequest } from '../../lib/apiClient.js'

export async function loadGameCheckout({ appUserId, gameId }) {
  const game = await apiRequest(`/games/${gameId}`)
  const [venue, images, participants, paymentMethods] = await Promise.all([
    apiRequest(`/venues/${game.venue_id}`).catch(() => null),
    apiRequest(`/game-images?game_id=${gameId}&image_status=active`).catch(() => []),
    apiRequest(`/game-participants?game_id=${gameId}`),
    apiRequest(`/user-payment-methods?user_id=${appUserId}`).catch(() => []),
  ])

  return {
    game,
    images,
    participants,
    paymentMethods,
    venue,
  }
}

export async function confirmGameCheckout({
  gameId,
  guestCount,
  isAddGuestsCheckout,
  userId,
}) {
  const endpoint = isAddGuestsCheckout
    ? `/games/${gameId}/booking-guests/add`
    : `/games/${gameId}/join`

  return apiRequest(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acting_user_id: userId, guest_count: guestCount }),
  })
}
