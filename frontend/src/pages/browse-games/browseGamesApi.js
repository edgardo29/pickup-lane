import { apiRequest } from '../../lib/apiClient.js'

export function loadBrowseGamesPage({ cursor = '', limit = 40, signal, startsOn }) {
  const params = new URLSearchParams({
    limit: String(limit),
  })

  if (startsOn) {
    params.set('starts_on', startsOn)
  }

  if (cursor) {
    params.set('cursor', cursor)
  }

  return apiRequest(`/games/browse?${params.toString()}`, { signal })
}
