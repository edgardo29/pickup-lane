import { MINIMUM_TOTAL_SPOTS } from './createGameData.js'
import { getPriceCents, serializePaymentMethods } from './createGamePayment.js'
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
