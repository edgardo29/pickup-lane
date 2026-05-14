import { apiRequest } from '../../lib/apiClient.js'

export const HOST_DEPOSIT_CENTS = 1000

export const formatOptions = ['3v3', '4v4', '5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']

export const environmentOptions = [
  { label: 'Indoor', value: 'indoor' },
  { label: 'Outdoor', value: 'outdoor' },
]

export const timeOptions = Array.from({ length: 24 * 12 }, (_, index) => {
  const totalMinutes = index * 5
  const hours = String(Math.floor(totalMinutes / 60)).padStart(2, '0')
  const minutes = String(totalMinutes % 60).padStart(2, '0')
  const value = `${hours}:${minutes}`

  return {
    label: formatTime(value),
    value,
  }
})

export const steps = [
  { id: 1, label: 'Basics' },
  { id: 2, label: 'Location' },
  { id: 3, label: 'Notes' },
  { id: 4, label: 'Review & Publish' },
]

export const initialForm = {
  date: getDefaultDate(),
  startTime: '18:00',
  endTime: '20:00',
  format: '7v7',
  environment: 'outdoor',
  totalSpots: 14,
  price: 25,
  venueName: '',
  street: '',
  city: '',
  state: '',
  zip: '',
  neighborhood: '',
  parkingNote: '',
  gameNotes: '',
}

export async function postJson(path, payload) {
  return apiRequest(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function patchJson(path, payload) {
  return apiRequest(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function loadEditableGame(gameId) {
  const game = await apiRequest(`/games/${gameId}`)
  const venue = await apiRequest(`/venues/${game.venue_id}`).catch(() => null)
  return { game, venue }
}

export function mapGameToForm(game, venue) {
  const startsAt = new Date(game.starts_at)
  const endsAt = new Date(game.ends_at)

  return {
    date: toDateInputValue(startsAt),
    startTime: toTimeInputValue(startsAt),
    endTime: toTimeInputValue(endsAt),
    format: game.format_label || '7v7',
    environment: game.environment_type || 'outdoor',
    totalSpots: game.total_spots || 14,
    price: Math.round((game.price_per_player_cents || 0) / 100),
    venueName: venue?.name || game.venue_name_snapshot || '',
    street: venue?.address_line_1 || getStreetFromAddressSnapshot(game.address_snapshot),
    city: venue?.city || game.city_snapshot || '',
    state: venue?.state || game.state_snapshot || '',
    zip: venue?.postal_code || '',
    neighborhood: venue?.neighborhood || game.neighborhood_snapshot || '',
    parkingNote: game.parking_notes || '',
    gameNotes: game.game_notes || '',
  }
}

export function buildReview(form) {
  return {
    date: new Intl.DateTimeFormat('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(`${form.date}T12:00:00`)),
    time: `${formatTime(form.startTime)} - ${formatTime(form.endTime)}`,
  }
}

export function buildDateTime(date, time) {
  return new Date(`${date}T${time}:00`).toISOString()
}

export function getMinimumSpotsForFormat(format) {
  const [homeSide, awaySide] = String(format || '').toLowerCase().split('v')
  const homeCount = Number(homeSide)
  const awayCount = Number(awaySide)

  if (!Number.isFinite(homeCount) || homeCount !== awayCount) {
    return 6
  }

  return Math.max(homeCount * 2, 6)
}

export function buildAddress(form) {
  const stateLine = [form.state.trim(), form.zip.trim()].filter(Boolean).join(' ')
  const cityLine = [form.city.trim(), stateLine].filter(Boolean).join(', ')
  return [form.street.trim(), cityLine].filter(Boolean).join(', ')
}

export function buildPreviewLocation(form) {
  return form.neighborhood || form.city || form.state || 'Location not set'
}

export function getExitPath(isEditMode, gameId) {
  return isEditMode && gameId ? `/games/${gameId}` : '/games'
}

export function validateStep(step, form) {
  if (step === 1) {
    if (form.date < getTodayDate()) {
      return 'Choose today or a future date.'
    }

    if (form.endTime <= form.startTime) {
      return 'End time must be after the start time.'
    }

    if (new Date(buildDateTime(form.date, form.startTime)) <= new Date()) {
      return 'Start time must be in the future.'
    }

    const minimumSpots = getMinimumSpotsForFormat(form.format)
    if (Number(form.totalSpots) < minimumSpots) {
      return `${form.format} games need at least ${minimumSpots} total spots.`
    }
  }

  if (step === 2) {
    const requiredFields = [
      ['venueName', 'venue name'],
      ['street', 'street address'],
      ['city', 'city'],
      ['state', 'state'],
      ['zip', 'ZIP code'],
    ]
    const missingField = requiredFields.find(([field]) => !form[field].trim())

    if (missingField) {
      return `Add a ${missingField[1]} before continuing.`
    }
  }

  return ''
}

export function validateCreateGame(form) {
  for (const step of [1, 2]) {
    const message = validateStep(step, form)
    if (message) {
      return { step, message }
    }
  }

  return null
}

export function clampDate(value) {
  if (!value) {
    return getTodayDate()
  }

  return value < getTodayDate() ? getTodayDate() : value
}

export function sanitizeMoney(value) {
  const digitsOnly = value.replace(/[^\d]/g, '')
  if (!digitsOnly) {
    return 0
  }

  return Math.min(Number(digitsOnly), 999)
}

export function formatPaymentMethod(paymentMethod) {
  if (!paymentMethod) {
    return 'Visa .... 4242'
  }

  return `${capitalize(paymentMethod.card_brand || 'card')} .... ${paymentMethod.card_last4}`
}

export function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(`2026-01-01T${value}:00`))
}

export function formatMoney(cents) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format((cents || 0) / 100)
}

export function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

export function getDefaultDate() {
  const date = new Date()
  date.setDate(date.getDate() + 10)
  return toDateInputValue(date)
}

export function getTodayDate() {
  return toDateInputValue(new Date())
}

function toDateInputValue(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function toTimeInputValue(date) {
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

function getStreetFromAddressSnapshot(addressSnapshot) {
  return addressSnapshot?.split(',')[0]?.trim() || ''
}
