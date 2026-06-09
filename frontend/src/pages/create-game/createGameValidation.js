import {
  environmentOptions,
  createGameFieldLimits,
  formatOptions,
  MINIMUM_TOTAL_SPOTS,
  playerGroupOptions,
  skillLevelOptions,
} from './createGameData.js'
import {
  getIncompletePaymentMethod,
  getPriceCents,
  serializePaymentMethods,
} from './createGamePayment.js'
import { buildDateTime, getTodayDate } from './createGameSchedule.js'

export function getMinimumSpotsForFormat(format) {
  const sideSize = getSideSizeForFormat(format)

  if (!sideSize) {
    return MINIMUM_TOTAL_SPOTS
  }

  return Math.max(sideSize * 2, MINIMUM_TOTAL_SPOTS)
}

export function validateStep(step, form) {
  if (step === 1) {
    const missingGameFields = [
      [!form.date, 'date', 'Choose a date.'],
      [!form.startTime, 'start time', 'Choose a start time.'],
      [!form.endTime, 'end time', 'Choose an end time.'],
      [!formatOptions.includes(form.format), 'format', 'Choose a game format.'],
      [
        !playerGroupOptions.some((option) => option.value === form.gamePlayerGroup),
        'player group',
        'Choose a player group.',
      ],
      [
        !skillLevelOptions.some((option) => option.value === form.skillLevel),
        'skill level',
        'Choose a skill level.',
      ],
      [
        !environmentOptions.some((option) => option.value === form.environment),
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

    if (new Date(buildDateTime(form.date, form.startTime)) <= new Date()) {
      return 'Start time must be in the future.'
    }

    const minimumSpots = getMinimumSpotsForFormat(form.format)
    if (Number(form.totalSpots) < minimumSpots) {
      return `${form.format} games need at least ${minimumSpots} total spots.`
    }

    if (!Number.isFinite(Number(form.price)) || Number(form.price) < 0) {
      return 'Price per player must be 0 or more.'
    }
  }

  if (step === 2) {
    const locationLengthError = validateFieldLengths([
      ['Venue name', form.venueName, createGameFieldLimits.venueName],
      ['Street address', form.street, createGameFieldLimits.street],
      ['City', form.city, createGameFieldLimits.city],
      ['ZIP code', form.zip, createGameFieldLimits.zip],
      ['Neighborhood', form.neighborhood, createGameFieldLimits.neighborhood],
      ['Parking note', form.parkingNote, createGameFieldLimits.parkingNote],
    ])
    if (locationLengthError) {
      return locationLengthError
    }

    const missingLocationFields = [
      [!form.venueName.trim(), 'venue name', 'Add venue name.'],
      [!form.street.trim(), 'street address', 'Add street address.'],
      [!form.city.trim(), 'city', 'Add city.'],
      [!form.state.trim(), 'state', 'Add state.'],
      [!form.zip.trim(), 'ZIP code', 'Add ZIP code.'],
    ].filter(([isMissing]) => isMissing)

    const missingMessage = getRequiredFieldsMessage(missingLocationFields)
    if (missingMessage) {
      return missingMessage
    }
  }

  if (step === 3) {
    const notesLengthError = validateFieldLengths([
      ['Game notes', form.gameNotes, createGameFieldLimits.gameNotes],
      ['Host rules', form.hostRules, createGameFieldLimits.hostRules],
    ])
    if (notesLengthError) {
      return notesLengthError
    }

    if (getIncompletePaymentMethod(form.paymentMethods)) {
      return 'Add payment method details before continuing.'
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

export function validateCreateGame(form) {
  for (const step of [1, 2, 3]) {
    const message = validateStep(step, form)
    if (message) {
      return { step, message }
    }
  }

  if (getPriceCents(form) > 0 && serializePaymentMethods(form.paymentMethods).length === 0) {
    return { step: 3, message: 'Add at least one host payment method.' }
  }

  return null
}

function getSideSizeForFormat(format) {
  const [homeSide, awaySide] = String(format || '').toLowerCase().split('v')
  const homeCount = Number(homeSide)
  const awayCount = Number(awaySide)

  if (!Number.isFinite(homeCount) || homeCount !== awayCount) {
    return 0
  }

  return homeCount
}
