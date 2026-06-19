import {
  environmentOptions,
  formatOptions,
  timeOptions,
} from '../../../create-game/createGameData.js'
import {
  clampDate,
  getDefaultDate,
  getTodayDate,
  toDateInputValue,
} from '../../../create-game/createGameSchedule.js'
import { getOfficialGameDateTimeInputs } from '../shared/adminOfficialGameDateTime.js'

export { US_STATE_OPTIONS } from '../../../../data/usStates.js'
export { clampDate, getTodayDate, toDateInputValue }

export const adminCreateOfficialGameSteps = [
  { id: 1, label: 'Basics' },
  { id: 2, label: 'Location' },
  { id: 3, label: 'Details' },
  { id: 4, label: 'Review' },
]

export const adminOfficialFormatOptions = formatOptions
export const adminOfficialEnvironmentOptions = environmentOptions
export const adminOfficialTimeOptions = timeOptions

export const initialAdminOfficialGameForm = {
  date: getDefaultDate(),
  startTime: '19:00',
  endTime: '20:00',
  timezone: 'America/Chicago',
  venueName: '',
  addressLine1: '',
  city: '',
  state: '',
  postalCode: '',
  countryCode: 'US',
  neighborhood: '',
  formatLabel: '5v5',
  environmentType: 'indoor',
  totalSpots: 10,
  price: 15,
  allowGuests: true,
  maxGuestsPerBooking: 2,
  waitlistEnabled: true,
  isChatEnabled: true,
  parkingNotes: '',
  reason: '',
}

function centsToMoney(value) {
  return Number(((Number(value) || 0) / 100).toFixed(2))
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

export function buildAdminOfficialReplacementForm(sourceGame) {
  const dateParts = getGameDateParts(sourceGame)

  return {
    ...initialAdminOfficialGameForm,
    ...dateParts,
    timezone: sourceGame.timezone || initialAdminOfficialGameForm.timezone,
    formatLabel: sourceGame.format_label || initialAdminOfficialGameForm.formatLabel,
    environmentType: sourceGame.environment_type || initialAdminOfficialGameForm.environmentType,
    totalSpots: sourceGame.total_spots || initialAdminOfficialGameForm.totalSpots,
    price: centsToMoney(sourceGame.price_per_player_cents),
    allowGuests: Boolean(sourceGame.allow_guests),
    maxGuestsPerBooking: sourceGame.max_guests_per_booking ?? initialAdminOfficialGameForm.maxGuestsPerBooking,
    waitlistEnabled: Boolean(sourceGame.waitlist_enabled),
    isChatEnabled: Boolean(sourceGame.is_chat_enabled),
    reason: `Replacement for official game ${sourceGame.id}.`,
  }
}
