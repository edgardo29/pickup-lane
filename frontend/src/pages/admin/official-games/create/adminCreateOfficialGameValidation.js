import { getTodayDate } from './adminCreateOfficialGameData.js'
import { buildOfficialGameIsoDateTime } from '../shared/adminOfficialGameDateTime.js'

export function getMinimumAdminOfficialSpots(format) {
  const [homeSide, awaySide] = String(format || '').toLowerCase().split('v')
  const homeCount = Number(homeSide)
  const awayCount = Number(awaySide)

  if (!Number.isFinite(homeCount) || homeCount !== awayCount) {
    return 6
  }

  return Math.max(homeCount * 2, 6)
}

export function validateAdminOfficialCreateStep(step, form) {
  if (step === 1) {
    if (form.date < getTodayDate()) {
      return 'Choose today or a future date.'
    }

    if (!form.startTime || !form.endTime) {
      return 'Choose a start and end time.'
    }

    if (form.endTime <= form.startTime) {
      return 'End time must be after the start time.'
    }

    if (!form.timezone.trim()) {
      return 'Add a timezone.'
    }

    try {
      const startsAt = new Date(
        buildOfficialGameIsoDateTime(form.date, form.startTime, form.timezone),
      )
      buildOfficialGameIsoDateTime(form.date, form.endTime, form.timezone)
      if (startsAt <= new Date()) {
        return 'Start time must be in the future.'
      }
    } catch (error) {
      return error.message || 'Enter a valid schedule.'
    }

    const minimumSpots = getMinimumAdminOfficialSpots(form.formatLabel)
    if (Number(form.totalSpots) < minimumSpots) {
      return `${form.formatLabel} games need at least ${minimumSpots} total spots.`
    }

    if (Number(form.price) < 0) {
      return 'Price cannot be negative.'
    }
  }

  if (step === 2) {
    const requiredVenueFields = [
      ['venueName', 'venue name'],
      ['addressLine1', 'street address'],
      ['city', 'city'],
      ['state', 'state'],
      ['postalCode', 'postal code'],
    ]
    const missingField = requiredVenueFields.find(([field]) => !String(form[field]).trim())

    if (missingField) {
      return `Add a ${missingField[1]}.`
    }
  }

  if (step === 3) {
    if (Number(form.maxGuestsPerBooking) < 0) {
      return 'Max guests cannot be negative.'
    }
  }

  return ''
}

export function validateAdminOfficialCreateForm(form) {
  for (const step of [1, 2, 3, 4]) {
    const message = validateAdminOfficialCreateStep(step, form)
    if (message) {
      return { step, message }
    }
  }

  return null
}
