export function formatRelativeTime(value) {
  const deltaMs = Date.now() - new Date(value).getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (deltaMs < hour) {
    return `${Math.max(1, Math.round(deltaMs / minute))}m`
  }

  if (deltaMs < day) {
    return `${Math.round(deltaMs / hour)}h`
  }

  return `${Math.round(deltaMs / day)}d`
}

export function formatFullDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}
