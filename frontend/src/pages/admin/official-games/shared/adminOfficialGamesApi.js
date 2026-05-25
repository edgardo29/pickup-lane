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

export async function listAdminOfficialGames({ firebaseUser, gameStatus = '' }) {
  const search = gameStatus ? `?game_status=${encodeURIComponent(gameStatus)}` : ''

  return apiRequest(`/admin/official-games${search}`, {
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

export async function uploadVenueImageBlob({ file, uploadHeaders, uploadUrl }) {
  const response = await fetch(uploadUrl, {
    method: 'PUT',
    headers: uploadHeaders,
    body: file,
  })

  if (!response.ok) {
    throw new Error(`Azure upload failed with status ${response.status}.`)
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
  const etag = await uploadVenueImageBlob({
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
}) {
  return apiRequest(`/games/${gameId}/cancel`, {
    method: 'POST',
    headers: await getAdminHeaders(firebaseUser, true),
    body: JSON.stringify(cancelReason ? { cancel_reason: cancelReason } : {}),
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

export async function listAdminOfficialGameUsers({ firebaseUser, query = '' }) {
  const search = query ? `?query=${encodeURIComponent(query)}` : ''

  return apiRequest(`/admin/lookups/users${search}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameVenues({ firebaseUser, query = '' }) {
  const search = query ? `?query=${encodeURIComponent(query)}` : ''

  return apiRequest(`/admin/lookups/venues${search}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminVenueImages({ firebaseUser, venueId }) {
  return apiRequest(`/admin/venues/${venueId}/images?image_status=active`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminOfficialGameParticipants({ firebaseUser, gameId }) {
  return apiRequest(`/admin/official-games/${gameId}/participants`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}
