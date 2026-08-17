import { APP_CHECK_HEADER_NAME, getAppCheckToken } from './appCheck.js'

const viteEnv = import.meta.env ?? {}

export const API_BASE_URL =
  viteEnv.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000'

export class ApiRequestError extends Error {
  constructor(message, { code = '', detail = null, status = 0 } = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.detail = detail
    this.status = status
  }
}

export async function apiRequest(path, options = {}) {
  const headers = {
    Accept: 'application/json',
    ...options.headers,
  }
  const appCheckToken = shouldAttachAppCheck(path)
    ? await getAppCheckToken()
    : null

  if (appCheckToken) {
    headers[APP_CHECK_HEADER_NAME] = appCheckToken
  }

  const response = await fetch(buildApiUrl(path), {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null)
    const detail = errorBody?.detail
    const code = getApiErrorCode(errorBody)
    throw new ApiRequestError(
      formatApiErrorMessage(detail, response.status),
      { code, detail, status: response.status },
    )
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export function shouldAttachAppCheck(path) {
  return !/^(https?:)?\/\//i.test(path) && !/^data:/i.test(path)
}

export function getApiErrorCode(errorBody) {
  const code = errorBody?.code || errorBody?.detail?.code || ''
  return typeof code === 'string' ? code : ''
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

  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message
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
