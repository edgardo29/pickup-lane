import { apiRequest } from '../../lib/apiClient.js'
import { listUserPaymentMethods } from '../../lib/paymentMethodsApi.js'

export async function patchHostEditGame(firebaseUser, gameId, payload) {
  if (!firebaseUser) {
    throw new Error('Sign in to edit this game.')
  }

  return apiRequest(`/games/${gameId}/host-edit`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function upsertHostCommunityGameDetails(firebaseUser, gameId, payload) {
  if (!firebaseUser) {
    throw new Error('Sign in to edit this game.')
  }

  return apiRequest(`/community-game-details/games/${gameId}/host-edit`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function publishCommunityGame(firebaseUser, payload) {
  if (!firebaseUser) {
    throw new Error('Sign in to publish a game.')
  }

  const response = await apiRequest('/community-games/publish', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return response.game
}

export async function loadEditableGame(firebaseUser, gameId) {
  if (!firebaseUser) {
    throw new Error('Sign in to edit this game.')
  }

  const game = await apiRequest(`/games/${gameId}`)
  const venue = await apiRequest(`/venues/${game.venue_id}`).catch(() => null)
  const communityDetails = await apiRequest(
    `/community-game-details/games/${gameId}/host-edit`,
    {
      headers: {
        Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
      },
    },
  )
    .catch((error) => {
      if (error?.status === 404) {
        return null
      }
      throw error
    })
  return { communityDetails, game, venue }
}

export async function loadHostPublishFees(firebaseUser) {
  if (!firebaseUser) {
    return []
  }

  return apiRequest('/host-publish-fees/me', {
    headers: {
      Authorization: `Bearer ${await firebaseUser.getIdToken()}`,
    },
  }).catch(() => [])
}

export async function loadUserPaymentMethods(firebaseUser) {
  if (!firebaseUser) {
    return []
  }

  return listUserPaymentMethods(firebaseUser).catch(() => [])
}
