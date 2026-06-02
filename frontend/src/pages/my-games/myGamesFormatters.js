export function formatTimeRange(start, end) {
  return `${formatStartTime(start)} - ${formatStartTime(end)}`
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

export function formatAgendaDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
    .format(new Date(value))
    .toUpperCase()
}

function formatStartTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}
