import { apiRequest } from './apiClient.js'

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

export function getNeedASubPost(postId) {
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
