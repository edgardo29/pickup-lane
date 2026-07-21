export function getFullName(user) {
  return `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'Player'
}

export function getInitials(user) {
  const first = user?.first_name?.[0] || 'P'
  const last = user?.last_name?.[0] || 'L'
  return `${first}${last}`.toUpperCase()
}

export function formatLocation(user, settings) {
  const city = settings.selected_city || user.home_city
  const state = settings.selected_state || user.home_state
  return [city, state].filter(Boolean).join(', ') || 'Not set'
}

export function formatMemberSince(value) {
  if (!value) {
    return 'Recently'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    year: 'numeric',
  }).format(new Date(value))
}

export function getNotificationSummary(settings) {
  return settings.email_notifications_enabled
    ? 'Email notifications on'
    : 'Email notifications off'
}

export function formatCreditAmount(cents = 0, currency = 'USD') {
  const amount = Math.max(0, cents) / 100
  const hasCents = cents % 100 !== 0

  return new Intl.NumberFormat('en-US', {
    currency,
    maximumFractionDigits: 2,
    minimumFractionDigits: hasCents ? 2 : 0,
    style: 'currency',
  }).format(amount)
}

export function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}
