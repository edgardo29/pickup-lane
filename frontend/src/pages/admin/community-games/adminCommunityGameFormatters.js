export function formatAdminCommunityDateTime(value, timeZone = undefined) {
  if (!value) {
    return 'No date'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return 'Invalid date'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
    ...(timeZone ? { timeZone } : {}),
  }).format(date)
}

export function formatAdminCommunityMoney(cents, currency = 'USD') {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency || 'USD',
  }).format(Number(cents || 0) / 100)
}

export function formatAdminCommunityStatus(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function shortAdminCommunityId(value) {
  return value ? String(value).slice(0, 8) : 'None'
}

export function formatAdminCommunityBoolean(value) {
  return value ? 'Yes' : 'No'
}
