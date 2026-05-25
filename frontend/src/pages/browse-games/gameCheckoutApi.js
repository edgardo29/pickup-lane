import { apiRequest } from '../../lib/apiClient.js'
import { listUserPaymentMethods } from '../../lib/paymentMethodsApi.js'

async function getAuthHeaders(firebaseUser) {
  if (!firebaseUser) {
    throw new Error('Sign in before starting checkout.')
  }

  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
  }
}

export async function loadGameCheckout({ firebaseUser, gameId }) {
  const game = await apiRequest(`/games/${gameId}`)
  const [venue, gameImages, venueImages, participants, paymentMethods] = await Promise.all([
    apiRequest(`/venues/${game.venue_id}`).catch(() => null),
    apiRequest(`/game-images?game_id=${gameId}&image_status=active`).catch(() => []),
    game.game_type === 'official'
      ? apiRequest(`/venue-images?venue_id=${game.venue_id}`).catch(() => [])
      : Promise.resolve([]),
    apiRequest(`/game-participants?game_id=${gameId}`),
    firebaseUser ? listUserPaymentMethods(firebaseUser).catch(() => []) : Promise.resolve([]),
  ])
  const images =
    game.game_type === 'official' && gameImages.length === 0 ? venueImages : gameImages

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

export async function createGameCheckoutPaymentIntent({
  firebaseUser,
  gameId,
  guestCount,
  paymentMethodId = '',
  returnUrl = '',
}) {
  const payload = {
    guest_count: guestCount,
  }
  if (paymentMethodId) {
    payload.payment_method_id = paymentMethodId
  }
  if (returnUrl) {
    payload.return_url = returnUrl
  }

  return apiRequest(`/checkout/games/${gameId}/payment-intent`, {
    method: 'POST',
    headers: {
      ...(await getAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function getGameCheckoutStatus({ bookingId, firebaseUser }) {
  return apiRequest(`/checkout/bookings/${bookingId}/status`, {
    headers: await getAuthHeaders(firebaseUser),
  })
}
