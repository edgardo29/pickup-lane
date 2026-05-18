export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000'

export class ApiRequestError extends Error {
  constructor(message, { detail = null, status = 0 } = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.detail = detail
    this.status = status
  }
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null)
    const detail = errorBody?.detail
    throw new ApiRequestError(
      typeof detail === 'string' ? detail : `Request failed with status ${response.status}`,
      { detail, status: response.status },
    )
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export function buildApiUrl(path) {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

export function buildMediaUrl(path) {
  if (!path) {
    return ''
  }

  if (/^(https?:)?\/\//i.test(path) || /^data:/i.test(path)) {
    return path
  }

  return buildApiUrl(path)
}
