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
}
