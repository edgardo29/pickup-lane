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
  const [venue, gameImages, venueImages, participants, paymentMethodsResult] = await Promise.all([
    apiRequest(`/venues/${game.venue_id}`).catch(() => null),
    apiRequest(`/game-images?game_id=${gameId}&image_status=active`).catch(() => []),
    game.game_type === 'official'
      ? apiRequest(`/venue-images?venue_id=${game.venue_id}`).catch(() => [])
      : Promise.resolve([]),
    // The player list requires sign-in.
    firebaseUser
      ? apiRequest(`/games/${gameId}/participants`, { headers: await getAuthHeaders(firebaseUser) })
      : Promise.resolve([]),
    firebaseUser && game.game_type === 'official' && game.payment_collection_type === 'in_app'
      ? listUserPaymentMethods(firebaseUser)
        .then((methods) => ({ methods, error: '' }))
        .catch(() => ({ methods: [], error: 'Saved cards could not be loaded. Try again.' }))
      : Promise.resolve({ methods: [], error: '' }),
  ])
  const images =
    game.game_type === 'official' && gameImages.length === 0 ? venueImages : gameImages

  return {
    game,
    images,
    participants,
    paymentMethods: paymentMethodsResult.methods,
    paymentMethodsError: paymentMethodsResult.error,
    venue,
  }
}

// Version of the paid-waitlist charge consent the player agrees to.
export const WAITLIST_AUTO_CHARGE_CONSENT_VERSION = 'waitlist-auto-charge-v1'

export async function confirmGameCheckout({
  firebaseUser,
  gameId,
  guestCount,
  isAddGuestsCheckout,
  waitlistPaymentMethodId = '',
}) {
  const endpoint = isAddGuestsCheckout
    ? `/games/${gameId}/booking-guests/add`
    : `/games/${gameId}/join`
  const payload = { guest_count: guestCount }
  // A paid official waitlist needs a saved card and consent to a later charge.
  if (waitlistPaymentMethodId) {
    payload.payment_method_id = waitlistPaymentMethodId
    payload.auto_charge_consent_accepted = true
    payload.auto_charge_consent_version = WAITLIST_AUTO_CHARGE_CONSENT_VERSION
  }

  return apiRequest(endpoint, {
    method: 'POST',
    headers: {
      ...(await getAuthHeaders(firebaseUser)),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function createGameCheckoutPaymentIntent({
  addGuests = false,
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

  // Added guests are paid for separately on the player's existing booking.
  const endpoint = addGuests
    ? `/checkout/games/${gameId}/guest-payment-intent`
    : `/checkout/games/${gameId}/payment-intent`

  return apiRequest(endpoint, {
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

// The price, the player's credit, and the amount due for a proposed party.
export async function loadGameCheckoutQuote({ addGuests, firebaseUser, gameId, guestCount }) {
  const params = new URLSearchParams({ guest_count: String(guestCount) })
  if (addGuests) {
    params.set('add_guests', 'true')
  }

  return apiRequest(`/checkout/games/${gameId}/quote?${params}`, {
    headers: await getAuthHeaders(firebaseUser),
  })
}
