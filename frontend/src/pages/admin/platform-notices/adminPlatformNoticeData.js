export const AUDIENCE_TYPE_ALL_ELIGIBLE = 'all_eligible_users'
export const AUDIENCE_TYPE_SELECTED = 'selected_users'

export const EMPTY_PLATFORM_NOTICE_FILTERS = {
  search: '',
  status: '',
}

export const EMPTY_PLATFORM_NOTICE_FORM = {
  audienceType: AUDIENCE_TYPE_ALL_ELIGIBLE,
  message: '',
  title: '',
}

export const PLATFORM_NOTICE_SELECTED_USER_LIMIT = 200
export const PLATFORM_NOTICE_HISTORY_SEARCH_MAX_LENGTH = 200
export const PLATFORM_NOTICE_HISTORY_SEARCH_MIN_MEANINGFUL_CHARS = 3

export const PLATFORM_NOTICE_STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Published', value: 'published' },
  { label: 'Cancelled', value: 'cancelled' },
]

export function createPlatformNoticeIdempotencyKey(operation = 'publish') {
  const suffix = typeof globalThis.crypto?.randomUUID === 'function'
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  return `platform-notice-${operation}-${suffix}`
}

export function userDisplayName(user) {
  if (user?.display_name) {
    return user.display_name
  }

  const name = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
  return name || user?.email || user?.id || 'Unknown user'
}

export function buildPlatformNoticeCreatePayload({
  form,
  idempotencyKey,
  selectedUsers,
}) {
  return {
    idempotency_key: idempotencyKey,
    title: form.title.trim(),
    message: form.message.trim(),
    audience_type: form.audienceType,
    selected_user_ids: form.audienceType === AUDIENCE_TYPE_SELECTED
      ? selectedUsers.map((user) => user.id)
      : [],
  }
}

export function buildPlatformNoticeCancelPayload(reason) {
  return {
    cancellation_reason: String(reason || '').trim(),
  }
}

export function validatePlatformNoticeContent(form) {
  const missingFields = [
    !form.title.trim() && 'title',
    !form.message.trim() && 'message',
  ].filter(Boolean)

  return missingFields.length ? `Enter ${missingFields.join(', ')}.` : ''
}

export function validatePlatformNoticeAudience(form, selectedUsers) {
  if (form.audienceType === AUDIENCE_TYPE_SELECTED && selectedUsers.length === 0) {
    return 'Select at least one active user.'
  }

  if (selectedUsers.length > PLATFORM_NOTICE_SELECTED_USER_LIMIT) {
    return `Selected notices cannot include more than ${PLATFORM_NOTICE_SELECTED_USER_LIMIT} users.`
  }

  return ''
}

export function canAddPlatformNoticeSelectedUser(selectedCandidate, selectedUsers) {
  if (!selectedCandidate) {
    return false
  }

  if (selectedUsers.length >= PLATFORM_NOTICE_SELECTED_USER_LIMIT) {
    return false
  }

  return !selectedUsers.some((user) => user.id === selectedCandidate.id)
}

export function normalizePlatformNoticeHistorySearch(value) {
  return String(value || '').trim().replace(/\s+/g, ' ').toLowerCase()
}

export function countPlatformNoticeHistorySearchMeaningfulCharacters(value) {
  return Array.from(String(value || '')).filter((character) => (
    /[\p{L}\p{N}]/u.test(character)
  )).length
}

export function getActivePlatformNoticeHistorySearch(
  value,
  minMeaningfulCharacters = PLATFORM_NOTICE_HISTORY_SEARCH_MIN_MEANINGFUL_CHARS,
) {
  const normalizedSearch = normalizePlatformNoticeHistorySearch(value)
  const meaningfulCharacters =
    countPlatformNoticeHistorySearchMeaningfulCharacters(normalizedSearch)

  return meaningfulCharacters >= minMeaningfulCharacters ? normalizedSearch : ''
}

export function formatPlatformNoticeLabel(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function formatPlatformNoticeDateTime(value) {
  if (!value) {
    return 'No date'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function platformNoticeAudienceLabel(notice) {
  if (!notice) {
    return 'Unknown audience'
  }

  if (notice.audience_type === AUDIENCE_TYPE_ALL_ELIGIBLE) {
    return 'All eligible users'
  }

  const count = notice.selected_recipient_count ?? 0
  return `${count} selected ${count === 1 ? 'user' : 'users'}`
}

export function platformNoticeStatusLabel(notice) {
  return notice?.cancelled_at ? 'Cancelled' : 'Published'
}

export function shortPlatformNoticeId(value) {
  return value ? String(value).slice(0, 8) : 'Unknown'
}
