// Games and posts show in their own local time zone, like Browse Games and
// Need a Sub; the viewer's device time zone never changes them.
const MARKET_TIME_ZONE = 'America/Chicago'

export function formatTimeRange(start, end, timeZone) {
  return `${formatStartTime(start, timeZone)} - ${formatStartTime(end, timeZone)}`
}

export function formatEnvironment(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ') : 'Pickup'
}

export function formatGamePlayerGroup(value) {
  const labels = {
    coed: 'Coed',
    men: 'Men',
    women: 'Women',
  }

  return labels[value] || (value ? formatEnvironment(value) : '')
}

export function formatSkillLevel(value) {
  const labels = {
    any: 'Any Skill',
    beginner: 'Beginner',
    recreational: 'Recreational',
    intermediate: 'Intermediate',
    advanced: 'Advanced',
    competitive: 'Competitive',
  }

  return labels[value] || (value ? formatEnvironment(value) : '')
}

export function formatPrice(cents, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100)
}

export function formatAgendaDate(value, timeZone) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: timeZone || MARKET_TIME_ZONE,
  })
    .format(new Date(value))
    .toUpperCase()
}

// The calendar date in the item's time zone, e.g. "2030-06-15", for grouping.
export function formatLocalDateKey(value, timeZone) {
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: timeZone || MARKET_TIME_ZONE,
  }).format(new Date(value))
}

function formatStartTime(value, timeZone) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: timeZone || MARKET_TIME_ZONE,
  }).format(new Date(value))
}
