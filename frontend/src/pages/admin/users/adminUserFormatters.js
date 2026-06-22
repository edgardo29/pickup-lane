const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
})

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export function formatAdminUserDate(value) {
  return value ? dateFormatter.format(new Date(value)) : 'No date'
}

export function formatAdminUserDateTime(value) {
  return value ? dateTimeFormatter.format(new Date(value)) : 'No date'
}

export function formatAdminUserLocation(value) {
  return [value?.home_city, value?.home_state].filter(Boolean).join(', ') || 'No location'
}

export function formatAdminUserStatus(value) {
  return String(value || '')
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Unknown'
}

export function shortAdminUserId(value) {
  return value ? String(value).slice(0, 8) : 'None'
}
