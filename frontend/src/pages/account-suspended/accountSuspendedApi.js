import { apiRequest } from '../../lib/apiClient.js'

export async function loadSuspendedAccountNotice(firebaseUser) {
  const token = await firebaseUser.getIdToken()
  return apiRequest('/account-suspended', {
    headers: { Authorization: `Bearer ${token}` },
  })
}
