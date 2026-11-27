import { apiRequest } from '../../lib/apiClient.js'

export async function readAuthReturnResource(pathname, currentUser) {
  const match = pathname.match(/^\/(games\/[^/]+|need-a-sub\/posts\/[^/]+)(?:\/.*)?$/)
  if (!match) return null
  return apiRequest(`/${match[1]}`, {
    headers: { Authorization: `Bearer ${await currentUser.getIdToken()}` },
  })
}
