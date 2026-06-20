const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDateTime(value) {
  if (!value) {
    return 'No date'
  }

  return dateTimeFormatter.format(new Date(value))
}

export function formatMoney(cents, currency = 'USD') {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency || 'USD',
  }).format(Number(cents || 0) / 100)
}

export function formatStatus(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function shortId(value) {
  return value ? String(value).slice(0, 8) : 'None'
}
