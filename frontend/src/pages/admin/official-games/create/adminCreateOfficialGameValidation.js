import {
  adminOfficialCreateFieldLimits,
  adminOfficialEnvironmentOptions,
  adminOfficialFormatOptions,
  adminOfficialPlayerGroupOptions,
  adminOfficialSkillLevelOptions,
  getTodayDate,
} from './adminCreateOfficialGameData.js'
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
    const missingGameFields = [
      [!form.date, 'date', 'Choose a date.'],
      [!form.startTime, 'start time', 'Choose a start time.'],
      [!form.endTime, 'end time', 'Choose an end time.'],
      [
        !adminOfficialFormatOptions.includes(form.formatLabel),
        'format',
        'Choose a game format.',
      ],
      [
        !adminOfficialPlayerGroupOptions.some(
          (option) => option.value === form.gamePlayerGroup,
        ),
        'player group',
        'Choose a player group.',
      ],
      [
        !adminOfficialSkillLevelOptions.some((option) => option.value === form.skillLevel),
        'skill level',
        'Choose a skill level.',
      ],
      [
        !adminOfficialEnvironmentOptions.some(
          (option) => option.value === form.environmentType,
        ),
        'indoor/outdoor',
        'Choose indoor or outdoor.',
      ],
      [form.totalSpots === '' || form.totalSpots == null, 'total spots', 'Choose total spots.'],
    ].filter(([isMissing]) => isMissing)

    const missingMessage = getRequiredFieldsMessage(missingGameFields)
    if (missingMessage) {
      return missingMessage
    }

    if (form.date < getTodayDate()) {
      return 'Choose today or a future date.'
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

    if (!Number.isFinite(Number(form.price)) || Number(form.price) < 0) {
      return 'Price per player must be 0 or more.'
    }
  }

  if (step === 2) {
    const locationLengthError = validateFieldLengths([
      ['Venue name', form.venueName, adminOfficialCreateFieldLimits.venueName],
      ['Street address', form.addressLine1, adminOfficialCreateFieldLimits.addressLine1],
      ['City', form.city, adminOfficialCreateFieldLimits.city],
      ['ZIP code', form.postalCode, adminOfficialCreateFieldLimits.postalCode],
      ['Neighborhood', form.neighborhood, adminOfficialCreateFieldLimits.neighborhood],
      ['Parking note', form.parkingNotes, adminOfficialCreateFieldLimits.parkingNotes],
    ])
    if (locationLengthError) {
      return locationLengthError
    }

    const missingLocationFields = [
      [!form.venueName.trim(), 'venue name', 'Add venue name.'],
      [!form.addressLine1.trim(), 'street address', 'Add street address.'],
      [!form.city.trim(), 'city', 'Add city.'],
      [!form.state.trim(), 'state', 'Add state.'],
      [!form.postalCode.trim(), 'ZIP code', 'Add ZIP code.'],
    ].filter(([isMissing]) => isMissing)

    const missingMessage = getRequiredFieldsMessage(missingLocationFields)
    if (missingMessage) {
      return missingMessage
    }
  }

  if (step === 3) {
    if (Number(form.maxGuestsPerBooking) < 0) {
      return 'Max guests cannot be negative.'
    }
  }

  return ''
}

function getRequiredFieldsMessage(missingFields) {
  if (missingFields.length === 0) {
    return ''
  }

  if (missingFields.length === 1) {
    return missingFields[0][2]
  }

  const labels = missingFields.map(([, label]) => label)
  return `Add ${formatList(labels)}.`
}

function formatList(labels) {
  if (labels.length === 1) {
    return labels[0]
  }

  if (labels.length === 2) {
    return `${labels[0]} and ${labels[1]}`
  }

  return `${labels.slice(0, -1).join(', ')}, and ${labels.at(-1)}`
}

function validateFieldLengths(fields) {
  for (const [label, value, maxLength] of fields) {
    if (String(value || '').length > maxLength) {
      return `${label} must be ${maxLength} characters or fewer.`
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
