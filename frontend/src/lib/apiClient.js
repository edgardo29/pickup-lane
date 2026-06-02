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
      formatApiErrorMessage(detail, response.status),
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

function formatApiErrorMessage(detail, status) {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return formatValidationDetail(detail[0])
  }

  return `Request failed with status ${status}`
}

function formatValidationDetail(detail) {
  const field = Array.isArray(detail?.loc) ? detail.loc.at(-1) : ''
  const fieldLabel = formatFieldLabel(field)

  if (detail?.type === 'string_too_long' && detail?.ctx?.max_length) {
    return `${fieldLabel} must be ${detail.ctx.max_length} characters or fewer.`
  }

  if (detail?.msg && fieldLabel) {
    return `${fieldLabel}: ${detail.msg}`
  }

  return detail?.msg || 'Request validation failed.'
}

function formatFieldLabel(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}
