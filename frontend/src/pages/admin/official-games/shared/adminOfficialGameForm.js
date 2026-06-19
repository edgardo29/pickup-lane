import {
  toDateInputValue,
  toTimeInputValue,
} from '../../../create-game/createGameSchedule.js'
import {
  buildOfficialGameIsoDateTime,
  getOfficialGameDateTimeInputs,
} from './adminOfficialGameDateTime.js'

const MAX_OFFICIAL_GUESTS = 2

export const officialGameStatusOptions = [
  { label: 'All statuses', value: '' },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Full', value: 'full' },
  { label: 'Cancelled', value: 'cancelled' },
  { label: 'Completed', value: 'completed' },
  { label: 'Abandoned', value: 'abandoned' },
]

export const officialGameFormatOptions = ['3v3', '4v4', '5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']

export const officialGameEnvironmentOptions = [
  { label: 'Indoor', value: 'indoor' },
  { label: 'Outdoor', value: 'outdoor' },
]

function getDefaultSchedule() {
  const startsAt = new Date()
  startsAt.setDate(startsAt.getDate() + 7)
  startsAt.setHours(19, 0, 0, 0)

  return {
    date: toDateInputValue(startsAt),
    startTime: toTimeInputValue(startsAt),
    endTime: '20:00',
  }
}

function centsToMoney(value) {
  return (Number(value ?? 0) / 100).toFixed(2)
}

function moneyToCents(value) {
  const normalized = String(value ?? '').replace(/[^\d.]/g, '')
  return Math.round((Number(normalized) || 0) * 100)
}

function clampGuests(value) {
  return Math.min(Math.max(Number(value) || 0, 0), MAX_OFFICIAL_GUESTS)
}

function cleanText(value) {
  return String(value ?? '').trim()
}

function getVenueNameForTitle(form) {
  return cleanText(form.venueName) || 'Official'
}

function buildGeneratedTitle(form) {
  return `${getVenueNameForTitle(form)} ${form.formatLabel}`.trim()
}

function getGameDateParts(game) {
  const timeZone = game?.timezone || 'America/Chicago'

  try {
    const startsAt = game?.starts_at
      ? getOfficialGameDateTimeInputs(game.starts_at, timeZone)
      : null
    const endsAt = game?.ends_at
      ? getOfficialGameDateTimeInputs(game.ends_at, timeZone)
      : null

    return {
      date: startsAt?.date || getDefaultSchedule().date,
      startTime: startsAt?.time || getDefaultSchedule().startTime,
      endTime: endsAt?.time || getDefaultSchedule().endTime,
    }
  } catch {
    return getDefaultSchedule()
  }
}

export function getAdminOfficialGameFormValues(game = null) {
  const schedule = getDefaultSchedule()

  if (!game) {
    return {
      title: '',
      venueId: '',
      venueName: '',
      date: schedule.date,
      startTime: schedule.startTime,
      endTime: schedule.endTime,
      timezone: 'America/Chicago',
      formatLabel: '5v5',
      environmentType: 'indoor',
      totalSpots: 10,
      price: '15.00',
      allowGuests: true,
      maxGuestsPerBooking: 2,
      waitlistEnabled: true,
      isChatEnabled: true,
      playerInstructions: '',
      parkingNotes: '',
    }
  }

  const dateParts = getGameDateParts(game)

  return {
    title: game.title ?? '',
    venueId: game.venue_id ?? '',
    venueName: game.venue_name_snapshot ?? '',
    date: dateParts.date,
    startTime: dateParts.startTime,
    endTime: dateParts.endTime,
    timezone: game.timezone ?? 'America/Chicago',
    formatLabel: game.format_label ?? '5v5',
    environmentType: game.environment_type ?? 'indoor',
    totalSpots: game.total_spots ?? 10,
    price: centsToMoney(game.price_per_player_cents),
    allowGuests: Boolean(game.allow_guests),
    maxGuestsPerBooking: clampGuests(game.max_guests_per_booking ?? 0),
    waitlistEnabled: Boolean(game.waitlist_enabled),
    isChatEnabled: Boolean(game.is_chat_enabled),
    playerInstructions: game.game_notes ?? '',
    parkingNotes: game.parking_notes ?? '',
  }
}

export function buildAdminOfficialGamePayload(form, venues = []) {
  if (!form.venueId) {
    throw new Error('Choose a venue.')
  }

  if (form.endTime <= form.startTime) {
    throw new Error('End time must be after the start time.')
  }

  const selectedVenue = venues.find((venue) => venue.id === form.venueId)
  const generatedForm = {
    ...form,
    venueName: selectedVenue?.name || form.venueName,
    maxGuestsPerBooking: clampGuests(form.maxGuestsPerBooking),
  }
  const timeZone = cleanText(form.timezone) || 'America/Chicago'

  const payload = {
    title: buildGeneratedTitle(generatedForm),
    starts_at: buildOfficialGameIsoDateTime(form.date, form.startTime, timeZone),
    ends_at: buildOfficialGameIsoDateTime(form.date, form.endTime, timeZone),
    timezone: timeZone,
    format_label: form.formatLabel,
    environment_type: form.environmentType,
    total_spots: Number(form.totalSpots),
    price_per_player_cents: moneyToCents(form.price),
    allow_guests: Boolean(form.allowGuests),
    max_guests_per_booking: generatedForm.maxGuestsPerBooking,
    waitlist_enabled: Boolean(form.waitlistEnabled),
    is_chat_enabled: Boolean(form.isChatEnabled),
    game_notes: cleanText(form.playerInstructions) || null,
    parking_notes: cleanText(form.parkingNotes) || null,
  }

  Object.keys(payload).forEach((key) => {
    if (payload[key] === undefined) {
      delete payload[key]
    }
  })

  return payload
}

export function getGeneratedAdminOfficialGameTitle(form, venues = []) {
  const selectedVenue = venues.find((venue) => venue.id === form.venueId)
  return buildGeneratedTitle({
    ...form,
    venueName: selectedVenue?.name || form.venueName,
  })
}

export function formatOfficialGameSchedule(game) {
  if (!game?.starts_at || !game?.ends_at) {
    return 'Schedule unavailable'
  }

  const day = new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeZone: game.timezone || 'America/Chicago',
  }).format(new Date(game.starts_at))
  const start = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: game.timezone || 'America/Chicago',
  }).format(new Date(game.starts_at))
  const end = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
    timeZone: game.timezone || 'America/Chicago',
  }).format(new Date(game.ends_at))

  return `${day}, ${start} - ${end}`
}

export function formatAdminGameMoney(cents, currency = 'USD') {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
  }).format((Number(cents) || 0) / 100)
}

export function getAdminUserLabel(user) {
  if (!user) {
    return 'Unknown user'
  }

  const name = [user.first_name, user.last_name].filter(Boolean).join(' ').trim()
  return name || user.email || user.id
}
