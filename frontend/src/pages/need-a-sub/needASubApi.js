import { apiRequest } from '../../lib/apiClient.js'

export function listNeedASubPosts(query = {}) {
  const params = new URLSearchParams()

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, value)
    }
  })

  const queryString = params.toString()
  return apiRequest(`/need-a-sub/posts${queryString ? `?${queryString}` : ''}`)
}

export async function listNeedASubPostCards(
  firebaseUser,
  {
    cursor = '',
    limit = 40,
    startsOn,
    view = 'all',
  } = {},
) {
  const params = new URLSearchParams()

  params.set('view', view)
  params.set('limit', String(limit))
  if (startsOn) {
    params.set('starts_on', startsOn)
  }
  if (cursor) {
    params.set('cursor', cursor)
  }

  const path = `/need-a-sub/posts/cards?${params.toString()}`

  if (firebaseUser) {
    return authenticatedRequest(firebaseUser, path)
  }

  return apiRequest(path)
}

export async function listMyNeedASubPosts(firebaseUser) {
  return authenticatedRequest(firebaseUser, '/need-a-sub/posts/mine')
}

export function getNeedASubPost(postId, firebaseUser = null) {
  if (firebaseUser) {
    return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}`)
  }

  return apiRequest(`/need-a-sub/posts/${postId}`)
}

export async function createNeedASubPost(firebaseUser, payload) {
  return authenticatedRequest(firebaseUser, '/need-a-sub/posts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateNeedASubPost(firebaseUser, postId, payload) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function requestNeedASubSpot(firebaseUser, postId, positionId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/requests`, {
    method: 'POST',
    body: JSON.stringify({ sub_post_position_id: positionId }),
  })
}

export async function listNeedASubPostRequests(firebaseUser, postId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/requests`)
}

export async function listMyNeedASubRequests(firebaseUser) {
  return authenticatedRequest(firebaseUser, '/need-a-sub/my-requests')
}

export async function acceptNeedASubRequest(firebaseUser, requestId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/requests/${requestId}/accept`, {
    method: 'PATCH',
  })
}

export async function declineNeedASubRequest(firebaseUser, requestId, reason = '') {
  return authenticatedRequest(firebaseUser, `/need-a-sub/requests/${requestId}/decline`, {
    method: 'PATCH',
    body: JSON.stringify({ reason: reason || null }),
  })
}

export async function cancelNeedASubRequest(firebaseUser, requestId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/requests/${requestId}/cancel`, {
    method: 'PATCH',
  })
}

export async function cancelNeedASubRequestByOwner(firebaseUser, requestId, reason = '') {
  return authenticatedRequest(firebaseUser, `/need-a-sub/requests/${requestId}/cancel-by-owner`, {
    method: 'PATCH',
    body: JSON.stringify({ reason: reason || null }),
  })
}

export async function cancelNeedASubPost(firebaseUser, postId, reason = '') {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/cancel`, {
    method: 'PATCH',
    body: JSON.stringify({ cancel_reason: reason || null }),
  })
}

export async function getNeedASubChat(firebaseUser, postId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/chat`)
}

export async function ensureNeedASubChat(firebaseUser, postId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/chat`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function listNeedASubChatMessages(
  firebaseUser,
  postId,
  { beforeCreatedAt = '', limit = 50 } = {},
) {
  const params = new URLSearchParams()

  if (beforeCreatedAt) {
    params.set('before_created_at', beforeCreatedAt)
  }
  if (limit) {
    params.set('limit', String(limit))
  }

  const queryString = params.toString()

  return authenticatedRequest(
    firebaseUser,
    `/need-a-sub/posts/${postId}/chat/messages${queryString ? `?${queryString}` : ''}`,
  )
}

export async function markNeedASubChatRead(firebaseUser, postId) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/chat/read`, {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function sendNeedASubChatMessage(
  firebaseUser,
  postId,
  chatId,
  messageBody,
) {
  return authenticatedRequest(firebaseUser, `/need-a-sub/posts/${postId}/chat/messages`, {
    method: 'POST',
    body: JSON.stringify({
      chat_id: chatId,
      message_body: messageBody,
    }),
  })
}

async function authenticatedRequest(firebaseUser, path, options = {}) {
  if (!firebaseUser) {
    throw new Error('Sign in to use Need a Sub.')
  }

  const idToken = await firebaseUser.getIdToken()

  return apiRequest(path, {
    ...options,
    headers: {
      Authorization: `Bearer ${idToken}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  })
}
