import { buildOfficialGameIsoDateTime, getOfficialGameDateTimeInputs } from '../shared/adminOfficialGameDateTime.js'
import {
  adminOfficialCreateFieldLimits,
  initialAdminOfficialGameForm,
} from '../create/adminCreateOfficialGameData.js'
import {
  getMinimumAdminOfficialSpots,
  validateAdminOfficialCreateStep,
} from '../create/adminCreateOfficialGameValidation.js'

export const adminEditOfficialGameSteps = [
  { id: 1, label: 'Game' },
  { id: 2, label: 'Details' },
  { id: 3, label: 'Review & Save', mobileLabel: 'Review' },
]

export const adminEditOfficialGameFieldLimits = {
  playerInstructions: 220,
  parkingNotes: 160,
  reason: 500,
}

function cleanText(value) {
  return String(value ?? '').trim()
}

function centsToMoney(value) {
  return Number(((Number(value) || 0) / 100).toFixed(2))
}

function moneyToCents(value) {
  const normalized = String(value ?? '').replace(/[^\d.]/g, '')
  return Math.round((Number(normalized) || 0) * 100)
}

function getGameDateParts(game) {
  const timeZone = game?.timezone || initialAdminOfficialGameForm.timezone

  try {
    const startsAt = game?.starts_at
      ? getOfficialGameDateTimeInputs(game.starts_at, timeZone)
      : null
    const endsAt = game?.ends_at
      ? getOfficialGameDateTimeInputs(game.ends_at, timeZone)
      : null

    return {
      date: startsAt?.date || initialAdminOfficialGameForm.date,
      startTime: startsAt?.time || initialAdminOfficialGameForm.startTime,
      endTime: endsAt?.time || initialAdminOfficialGameForm.endTime,
    }
  } catch {
    return {
      date: initialAdminOfficialGameForm.date,
      startTime: initialAdminOfficialGameForm.startTime,
      endTime: initialAdminOfficialGameForm.endTime,
    }
  }
}

export function buildAdminOfficialEditForm(game) {
  const dateParts = getGameDateParts(game)
  const addressParts = parseAddressSnapshot(game?.address_snapshot)

  return {
    ...initialAdminOfficialGameForm,
    ...dateParts,
    timezone: game?.timezone || initialAdminOfficialGameForm.timezone,
    venueName: game?.venue_name_snapshot || '',
    addressLine1: addressParts.addressLine1,
    city: game?.city_snapshot || addressParts.city,
    state: game?.state_snapshot || addressParts.state,
    postalCode: addressParts.postalCode,
    neighborhood: game?.neighborhood_snapshot || '',
    formatLabel: game?.format_label || initialAdminOfficialGameForm.formatLabel,
    gamePlayerGroup: game?.game_player_group || initialAdminOfficialGameForm.gamePlayerGroup,
    skillLevel: game?.skill_level || initialAdminOfficialGameForm.skillLevel,
    environmentType: game?.environment_type || initialAdminOfficialGameForm.environmentType,
    totalSpots: game?.total_spots ?? initialAdminOfficialGameForm.totalSpots,
    price: centsToMoney(game?.price_per_player_cents),
    allowGuests: Boolean(game?.allow_guests),
    maxGuestsPerBooking: game?.max_guests_per_booking ?? initialAdminOfficialGameForm.maxGuestsPerBooking,
    waitlistEnabled: Boolean(game?.waitlist_enabled),
    isChatEnabled: Boolean(game?.is_chat_enabled),
    parkingNotes: game?.parking_notes || '',
    playerInstructions: game?.game_notes || '',
    reason: '',
  }
}

function parseAddressSnapshot(addressSnapshot) {
  const parts = String(addressSnapshot || '').split(',').map((part) => part.trim())
  const statePostal = parts[2]?.split(/\s+/).filter(Boolean) || []

  return {
    addressLine1: parts[0] || '',
    city: parts[1] || '',
    state: statePostal[0] || '',
    postalCode: statePostal.slice(1).join(' '),
  }
}

export function buildAdminOfficialEditPayload(form) {
  const timeZone = cleanText(form.timezone) || 'America/Chicago'
  const payload = {
    title: `${cleanText(form.venueName) || 'Official'} ${form.formatLabel}`.trim(),
    starts_at: buildOfficialGameIsoDateTime(form.date, form.startTime, timeZone),
    ends_at: buildOfficialGameIsoDateTime(form.date, form.endTime, timeZone),
    timezone: timeZone,
    format_label: form.formatLabel,
    game_player_group: form.gamePlayerGroup,
    skill_level: form.skillLevel,
    environment_type: form.environmentType,
    total_spots: Number(form.totalSpots),
    price_per_player_cents: moneyToCents(form.price),
    allow_guests: Boolean(form.allowGuests),
    max_guests_per_booking: Number(form.maxGuestsPerBooking),
    waitlist_enabled: Boolean(form.waitlistEnabled),
    is_chat_enabled: Boolean(form.isChatEnabled),
    game_notes: cleanText(form.playerInstructions) || null,
    parking_notes: cleanText(form.parkingNotes) || null,
  }

  const reason = cleanText(form.reason)
  if (reason) {
    payload.reason = reason
  }

  return payload
}

export function validateAdminOfficialEditStep(step, form) {
  if (step === 1) {
    return validateAdminOfficialCreateStep(1, form)
  }

  if (step === 2) {
    const minimumSpots = getMinimumAdminOfficialSpots(form.formatLabel)
    if (Number(form.totalSpots) < minimumSpots) {
      return `${form.formatLabel} games need at least ${minimumSpots} total spots.`
    }

    if (Number(form.maxGuestsPerBooking) < 0 || Number(form.maxGuestsPerBooking) > 2) {
      return 'Max guests must be between 0 and 2.'
    }

    const lengthError = validateFieldLengths([
      ['Player instructions', form.playerInstructions, adminEditOfficialGameFieldLimits.playerInstructions],
      ['Parking note', form.parkingNotes, adminEditOfficialGameFieldLimits.parkingNotes],
      ['Internal reason', form.reason, adminEditOfficialGameFieldLimits.reason],
      ['Venue name', form.venueName, adminOfficialCreateFieldLimits.venueName],
    ])
    if (lengthError) {
      return lengthError
    }
  }

  return ''
}

export function validateAdminOfficialEditForm(form) {
  for (const step of [1, 2, 3]) {
    const message = validateAdminOfficialEditStep(step, form)
    if (message) {
      return { step, message }
    }
  }

  return null
}

function validateFieldLengths(fields) {
  for (const [label, value, maxLength] of fields) {
    if (String(value || '').length > maxLength) {
      return `${label} must be ${maxLength} characters or fewer.`
    }
  }

  return ''
}
