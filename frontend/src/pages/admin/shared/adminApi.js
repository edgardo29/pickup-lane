import { apiRequest } from '../../../lib/apiClient.js'

export async function getAdminHeaders(firebaseUser, includeJson = false) {
  if (!firebaseUser) {
    throw new Error('Sign in with an authorized staff account.')
  }

  const token = await firebaseUser.getIdToken()
  return {
    Authorization: `Bearer ${token}`,
    ...(includeJson ? { 'Content-Type': 'application/json' } : {}),
  }
}

export async function fetchAdminMe({ firebaseUser, forceRefresh = false }) {
  if (!firebaseUser) {
    return null
  }

  const token = await firebaseUser.getIdToken(forceRefresh)

  try {
    return await apiRequest('/admin/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
  } catch (error) {
    if (!forceRefresh && error?.status === 401) {
      return fetchAdminMe({ firebaseUser, forceRefresh: true })
    }

    throw error
  }
}

export async function fetchAdminActionCenter({ firebaseUser }) {
  return apiRequest('/admin/action-center', {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function listAdminActions({
  actionType = '',
  firebaseUser,
  limit = 100,
} = {}) {
  const searchParams = new URLSearchParams()

  if (actionType.trim()) {
    searchParams.set('action_type', actionType.trim())
  }

  searchParams.set('limit', String(limit))

  return apiRequest(`/admin/actions?${searchParams.toString()}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}

export async function getAdminAction({ adminActionId, firebaseUser }) {
  return apiRequest(`/admin/actions/${adminActionId}`, {
    headers: await getAdminHeaders(firebaseUser),
  })
}
