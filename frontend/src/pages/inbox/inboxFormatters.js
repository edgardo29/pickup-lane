export function formatRelativeTime(value) {
  if (!value) {
    return ''
  }

  const deltaMs = Date.now() - new Date(value).getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (Number.isNaN(deltaMs)) {
    return ''
  }

  if (deltaMs < 0) {
    return 'Now'
  }

  if (deltaMs < hour) {
    return `${Math.max(1, Math.round(deltaMs / minute))}m ago`
  }

  if (deltaMs < day) {
    return `${Math.round(deltaMs / hour)}h ago`
  }

  return ''
}

export function formatSubjectDateTime(value, timeZone) {
  if (!value) {
    return ''
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const formatOptions = getTimeZoneOptions(timeZone)
  const datePart = new Intl.DateTimeFormat('en-US', {
    ...formatOptions,
    day: 'numeric',
    month: 'long',
    weekday: 'long',
    year: 'numeric',
  }).format(date)
  const timePart = new Intl.DateTimeFormat('en-US', {
    ...formatOptions,
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)

  return `${datePart} at ${timePart}`
}

export function formatNotificationDate(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(value))
}

export function formatNotificationDateTime(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const formatted = new Intl.DateTimeFormat('en-US', {
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(date)

  return formatted
}

function getTimeZoneOptions(timeZone) {
  if (!timeZone) {
    return {}
  }

  try {
    new Intl.DateTimeFormat('en-US', { timeZone }).format(new Date())
    return { timeZone }
  } catch {
    return {}
  }
}
