import { apiRequest } from './apiClient.js'

export function checkEmailAvailability(email) {
  const encodedEmail = encodeURIComponent(email)

  return apiRequest(`/auth/email-availability?email=${encodedEmail}`)
}

export async function getAuthenticatedAppUser(firebaseUser, forceRefresh = false) {
  if (!firebaseUser) {
    return null
  }

  const idToken = await firebaseUser.getIdToken(forceRefresh)

  try {
    return await apiRequest('/auth/me', {
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    })
  } catch (error) {
    if (!forceRefresh && error?.status === 401) {
      const refreshedToken = await firebaseUser.getIdToken(true)

      return apiRequest('/auth/me', {
        headers: {
          Authorization: `Bearer ${refreshedToken}`,
        },
      })
    }

    throw error
  }
}

export function syncFirebaseUser(firebaseUser) {
  if (!firebaseUser?.uid || !firebaseUser?.email) {
    return null
  }

  return apiRequest('/auth/sync-user', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      auth_user_id: firebaseUser.uid,
      email: firebaseUser.email,
      email_verified: Boolean(firebaseUser.emailVerified),
    }),
  })
}

export async function deleteAuthenticatedAccount(firebaseUser, confirmation) {
  if (!firebaseUser) {
    throw new Error('Sign in before deleting your account.')
  }

  const idToken = await firebaseUser.getIdToken()

  return apiRequest('/auth/account', {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ confirmation }),
  })
}

export async function cleanupUnfinishedAccount(firebaseUser) {
  if (!firebaseUser) {
    return null
  }

  const idToken = await firebaseUser.getIdToken()

  return apiRequest('/auth/unfinished-account', {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${idToken}`,
    },
  })
}
