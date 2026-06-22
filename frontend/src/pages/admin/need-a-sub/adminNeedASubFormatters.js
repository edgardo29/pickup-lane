export function formatAdminNeedASubDateTime(value, timeZone = undefined) {
  if (!value) return 'Not recorded'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Invalid date'

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
      ...(timeZone ? { timeZone } : {}),
    }).format(date)
  } catch {
    return 'Invalid date'
  }
}

export function formatAdminNeedASubMoney(cents, currency = 'USD') {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency || 'USD',
  }).format(Number(cents || 0) / 100)
}

export function formatAdminNeedASubStatus(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function formatAdminNeedASubPosition(positionLabel, playerGroup) {
  const group = playerGroup === 'open'
    ? 'Any'
    : formatAdminNeedASubStatus(playerGroup)
  return `${group} ${formatAdminNeedASubStatus(positionLabel)}`
}

export function shortAdminNeedASubId(value) {
  return value ? String(value).slice(0, 8) : 'None'
}
