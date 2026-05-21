export function buildDateTime(date, time) {
  return new Date(`${date}T${time}:00`).toISOString()
}

export function clampDate(value) {
  if (!value) {
    return getTodayDate()
  }

  return value < getTodayDate() ? getTodayDate() : value
}

export function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(`2026-01-01T${value}:00`))
}

export function getDefaultDate() {
  const date = new Date()
  date.setDate(date.getDate() + 10)
  return toDateInputValue(date)
}

export function getTodayDate() {
  return toDateInputValue(new Date())
}

export function toDateInputValue(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function toTimeInputValue(date) {
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}
