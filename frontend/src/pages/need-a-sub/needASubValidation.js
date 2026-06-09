import {
  ENVIRONMENT_OPTIONS,
  FORMAT_OPTIONS,
  GROUP_OPTIONS,
  MAX_SUB_ROWS,
  MAX_TOTAL_SUBS,
  needASubFieldLimits,
  SKILL_OPTIONS,
  getAnyExclusivePositionConflict,
  positionsAreCompatibleWithPostGroup,
} from './needASubData.js'
import { formatPositionLabel } from './needASubFormatters.js'

export function validateNeedASubForm(form) {
  const gameError = validateNeedASubCreateStep('game', form)
  if (gameError) {
    return gameError
  }

  const locationError = validateNeedASubCreateStep('location', form)
  if (locationError) {
    return locationError
  }

  const subsError = validateNeedASubCreateStep('subs', form)
  if (subsError) {
    return subsError
  }

  const notesError = validateNeedASubCreateStep('notes', form)
  if (notesError) {
    return notesError
  }

  return ''
}

export function validateNeedASubCreateStep(stepKey, form) {
  if (stepKey === 'game') {
    return validateGameStep(form)
  }
  if (stepKey === 'subs') {
    return validateSubsStep(form)
  }
  if (stepKey === 'location') {
    return validateLocationStep(form)
  }
  if (stepKey === 'notes') {
    return validateNotesStep(form)
  }

  return ''
}

export function getFirstInvalidNeedASubCreateStep(steps, form) {
  for (let index = 0; index < steps.length; index += 1) {
    const error = validateNeedASubCreateStep(steps[index].key, form)
    if (error) {
      return { error, index }
    }
  }

  return { error: '', index: -1 }
}

function validateGameStep(form) {
  const missingGameFields = [
    [!form.date, 'date', 'Choose a date.'],
    [!form.startTime, 'start time', 'Choose a start time.'],
    [!form.endTime, 'end time', 'Choose an end time.'],
    [!FORMAT_OPTIONS.includes(form.formatLabel), 'format', 'Choose a game format.'],
    [
      !GROUP_OPTIONS.some((option) => option.value === form.gamePlayerGroup),
      'player group',
      'Choose a player group.',
    ],
    [
      !SKILL_OPTIONS.some((option) => option.value === form.skillLevel),
      'skill level',
      'Choose a skill level.',
    ],
    [
      !ENVIRONMENT_OPTIONS.some((option) => option.value === form.environment),
      'indoor/outdoor',
      'Choose indoor or outdoor.',
    ],
  ].filter(([isMissing]) => isMissing)

  const missingMessage = getRequiredFieldsMessage(missingGameFields)
  if (missingMessage) {
    return missingMessage
  }

  const startsAt = new Date(`${form.date}T${form.startTime}:00`)
  const endsAt = new Date(`${form.date}T${form.endTime}:00`)

  if (startsAt <= new Date()) {
    return 'Choose a future date and time.'
  }
  if (endsAt <= startsAt) {
    return 'End time must be after start time.'
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

function validateSubsStep(form) {
  if (!form.positions.length || form.positions.some((position) => Number(position.spots_needed) < 1)) {
    return 'Add at least one valid Sub requirement.'
  }

  const totalSpotsNeeded = form.positions.reduce(
    (sum, position) => sum + Number(position.spots_needed || 0),
    0,
  )
  if (form.positions.length > MAX_SUB_ROWS || totalSpotsNeeded > MAX_TOTAL_SUBS) {
    return `Need a Sub posts can include up to ${MAX_TOTAL_SUBS} total Subs.`
  }

  if (form.positions.some((position) => !position.position_label || !position.player_group)) {
    return 'Choose a player group for each sub requirement.'
  }

  if (!positionsAreCompatibleWithPostGroup(form.positions, form.gamePlayerGroup)) {
    return 'Sub requirements must match the selected player group.'
  }

  const positionKeys = new Set()
  for (const position of form.positions) {
    const key = `${position.position_label}:${position.player_group}`
    if (positionKeys.has(key)) {
      return 'Each position and player group row must be unique.'
    }
    positionKeys.add(key)
  }

  const anyConflict = getAnyExclusivePositionConflict(form.positions)
  if (anyConflict) {
    return `Any ${formatPositionLabel(anyConflict)} cannot be combined with Men or Women rows.`
  }

  return ''
}

function validateLocationStep(form) {
  const locationLengthError = validateFieldLengths([
    ['Venue name', form.locationName, needASubFieldLimits.locationName],
    ['Street address', form.addressLine1, needASubFieldLimits.addressLine1],
    ['City', form.city, needASubFieldLimits.city],
    ['ZIP', form.postalCode, needASubFieldLimits.postalCode],
    ['Neighborhood', form.neighborhood, needASubFieldLimits.neighborhood],
  ])
  if (locationLengthError) {
    return locationLengthError
  }

  const missingLocationFields = [
    [!form.locationName.trim(), 'venue name', 'Add venue name.'],
    [!form.addressLine1.trim(), 'street address', 'Add street address.'],
    [!form.city.trim(), 'city', 'Add city.'],
    [!form.state.trim(), 'state', 'Add state.'],
    [!form.postalCode.trim(), 'ZIP code', 'Add ZIP code.'],
  ].filter(([isMissing]) => isMissing)

  const missingMessage = getRequiredFieldsMessage(missingLocationFields)
  if (missingMessage) {
    return missingMessage
  }

  return ''
}

function validateNotesStep(form) {
  const notesLengthError = validateFieldLengths([
    ['Price due at venue', form.priceDue, needASubFieldLimits.priceDue],
    ['Notes', form.notes, needASubFieldLimits.notes],
  ])
  if (notesLengthError) {
    return notesLengthError
  }

  const priceDue = String(form.priceDue || '').trim()
  if (priceDue && (!Number.isFinite(Number(priceDue)) || Number(priceDue) < 0)) {
    return 'Enter a valid venue price or leave it blank.'
  }

  return ''
}

function validateFieldLengths(fields) {
  for (const [label, value, maxLength] of fields) {
    if (String(value || '').length > maxLength) {
      return `${label} must be ${maxLength} characters or fewer.`
    }
  }

  return ''
}
