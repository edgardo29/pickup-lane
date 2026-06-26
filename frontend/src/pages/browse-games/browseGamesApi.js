import { apiRequest } from '../../lib/apiClient.js'

export function loadBrowseGamesPage({ cursor = '', limit = 40, startsOn }) {
  const params = new URLSearchParams({
    starts_on: startsOn,
    limit: String(limit),
  })

  if (cursor) {
    params.set('cursor', cursor)
  }

  return apiRequest(`/games/browse?${params.toString()}`)
}
