import { apiRequest } from '../../../../lib/apiClient.js'

async function getAdminHeaders(firebaseUser, includeJson = false) {
  if (!firebaseUser) {
    throw new Error('Sign in as an admin before managing official games.')
  }

  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
    ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
  }
}

export async function listAdminOfficialGames({
  cursor = '',
  firebaseUser,
  limit = 24,
  search = '',
  startsOn = '',
  view = 'active',
}) {
  const searchParams = new URLSearchParams()

  if (view) {
    searchParams.set('view', view)
  }

  if (search) {
    searchParams.set('search', search)
  }

  if (startsOn) {
    searchParams.set('starts_on', startsOn)
  }

  if (limit) {
    searchParams.set('limit', String(limit))
  }

  if (cursor) {
    searchParams.set('cursor', cursor)
  }

  const queryString = searchParams.toString()

  return apiRequest(`/admin/official-games${queryString ? `?${queryString}` : ''}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function createAdminOfficialGame({ firebaseUser, payload }) {
  return apiRequest('/admin/official-games', {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(payload),
  })
}

export async function assertAdminVenueImageUploadsReady({ firebaseUser }) {
  return apiRequest('/admin/venue-images/upload-readiness', {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function createAdminVenueImageUploadUrl({
  file,
  firebaseUser,
  isPrimary = false,
  sortOrder = 0,
  venueId,
}) {
  return apiRequest(`/admin/venues/${venueId}/images/upload-url`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      file_name: file.name,
      content_type: file.type,
      size_bytes: file.size,
      image_role: isPrimary ? 'card' : 'gallery',
      is_primary: isPrimary,
      sort_order: sortOrder,
    }),
  })
}

export async function uploadVenueImageObject({ file, uploadHeaders, uploadUrl }) {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: uploadHeaders,
    body: file,
  })

  if (!response.ok) {
    throw new Error(`Image upload failed with status ${response.status}.`)
  }

  return response.headers.get('etag')
}

export async function completeAdminVenueImageUpload({
  etag,
  firebaseUser,
  venueImageId,
}) {
  return apiRequest(`/admin/venue-images/${venueImageId}/complete`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(etag ? { etag } : {}),
  })
}

export async function uploadAdminVenueImage({
  file,
  firebaseUser,
  isPrimary = false,
  sortOrder = 0,
  venueId,
}) {
  const uploadTicket = await createAdminVenueImageUploadUrl({
    file,
    firebaseUser,
    isPrimary,
    sortOrder,
    venueId,
  })
  const etag = await uploadVenueImageObject({
    file,
    uploadHeaders: uploadTicket.upload_headers,
    uploadUrl: uploadTicket.upload_url,
  })

  return completeAdminVenueImageUpload({
    etag,
    firebaseUser,
    venueImageId: uploadTicket.image.id,
  })
}

export async function getAdminOfficialGame({ firebaseUser, gameId }) {
  return apiRequest(`/admin/official-games/${gameId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function updateAdminOfficialGame({ firebaseUser, gameId, payload }) {
  return apiRequest(`/admin/official-games/${gameId}`, {
    method: 'PATCH',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(payload),
  })
}

export async function cancelAdminOfficialGame({
  cancelReason = '',
  firebaseUser,
  gameId,
  previewToken,
}) {
  return apiRequest(`/admin/official-games/${gameId}/cancel`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      preview_token: previewToken,
      reason: cancelReason,
    }),
  })
}

export async function previewAdminOfficialGameCancellation({
  firebaseUser,
  gameId,
}) {
  return apiRequest(`/admin/official-games/${gameId}/cancel-preview`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function assignAdminOfficialGameHost({
  firebaseUser,
  gameId,
  hostUserId,
  reason,
}) {
  return apiRequest(`/admin/official-games/${gameId}/host`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      host_user_id: hostUserId,
      ...(reason ? { reason } : {}),
    }),
  })
}

export async function removeAdminOfficialGameHost({ firebaseUser, gameId, reason }) {
  return apiRequest(`/admin/official-games/${gameId}/host`, {
    method: 'DELETE',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(reason ? { reason } : {}),
  })
}

export async function addAdminOfficialGamePlayer({
  firebaseUser,
  gameId,
  userId,
  reason,
}) {
  return apiRequest(`/admin/official-games/${gameId}/players`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify({
      user_id: userId,
      ...(reason ? { reason } : {}),
    }),
  })
}

export async function removeAdminOfficialGamePlayer({
  firebaseUser,
  gameId,
  participantId,
  reason,
}) {
  return apiRequest(`/admin/official-games/${gameId}/participants/${participantId}`, {
    method: 'DELETE',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(reason ? { reason } : {}),
  })
}

export async function previewAdminOfficialGamePlayerRemoval({
  firebaseUser,
  gameId,
  participantId,
}) {
  return apiRequest(
    `/admin/official-games/${gameId}/participants/${participantId}/remove-preview`,
    {
      method: 'POST',
      headers: await getAdminHeaders(firebaseUser),
    },
  )
}

export async function executeAdminOfficialGamePlayerRemoval({
  firebaseUser,
  gameId,
  participantId,
  previewToken,
  outcome,
  reason,
}) {
  return apiRequest(
    `/admin/official-games/${gameId}/participants/${participantId}/remove`,
    {
      method: 'POST',
      headers: await getAdminHeaders(firebaseUser, true),
      body: JSON.stringify({
        preview_token: previewToken,
        outcome,
        reason,
      }),
    },
  )
}

export async function searchAdminOfficialGameUsers({
  firebaseUser,
  gameId,
  limit = 10,
  query,
  signal,
}) {
  const searchParams = new URLSearchParams({
    q: query,
    limit: String(limit),
  })

  return apiRequest(
    `/admin/official-games/${gameId}/user-search?${searchParams.toString()}`,
    {
      headers: await getAdminHeaders(firebaseUser),
      signal,
    },
  )
}

export async function listOfficialGameVenueImages({ venueId }) {
  return apiRequest(`/venue-images?venue_id=${encodeURIComponent(venueId)}`)
}

export async function listAdminOfficialGameParticipants({ firebaseUser, gameId }) {
  return apiRequest(`/admin/official-games/${gameId}/participants`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameChatRooms({ firebaseUser, gameId }) {
  return apiRequest(`/game-chats?game_id=${encodeURIComponent(gameId)}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameChatMessages({
  chatId,
  firebaseUser,
  limit = 50,
}) {
  const searchParams = new URLSearchParams({
    chat_id: chatId,
    limit: String(limit),
  })

  return apiRequest(`/chat-messages?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameBookings({ firebaseUser, gameId }) {
  return apiRequest(`/admin/official-games/${gameId}/bookings`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameWaitlist({ firebaseUser, gameId }) {
  return apiRequest(`/admin/official-games/${gameId}/waitlist`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminOfficialGameMoney({ firebaseUser, gameId }) {
  return apiRequest(`/admin/official-games/${gameId}/money`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}
