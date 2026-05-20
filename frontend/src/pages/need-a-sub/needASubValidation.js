import { MAX_SUB_ROWS, MAX_TOTAL_SUBS } from './needASubData.js'

export function validateNeedASubForm(form) {
  const startsAt = new Date(`${form.date}T${form.startTime}:00`)
  const endsAt = new Date(`${form.date}T${form.endTime}:00`)

  if (!form.date || startsAt <= new Date()) {
    return 'Choose a future date and time.'
  }
  if (endsAt <= startsAt) {
    return 'End time must be after start time.'
  }
  if (!form.environment) {
    return 'Choose indoor or outdoor.'
  }
  if (
    !form.locationName.trim() ||
    !form.addressLine1.trim() ||
    !form.city.trim() ||
    !form.state.trim() ||
    !form.postalCode.trim()
  ) {
    return 'Complete the location fields.'
  }
  if (!form.positions.length || form.positions.some((position) => Number(position.spots_needed) < 1)) {
    return 'Add at least one valid Sub requirement.'
  }

  const priceDue = String(form.priceDue || '').trim()
  if (priceDue && (!Number.isFinite(Number(priceDue)) || Number(priceDue) < 0)) {
    return 'Enter a valid venue price or leave it blank.'
  }

  const totalSpotsNeeded = form.positions.reduce(
    (sum, position) => sum + Number(position.spots_needed || 0),
    0,
  )
  if (form.positions.length > MAX_SUB_ROWS || totalSpotsNeeded > MAX_TOTAL_SUBS) {
    return `Need a Sub posts can include up to ${MAX_TOTAL_SUBS} total Subs.`
  }

  const positionKeys = new Set()
  for (const position of form.positions) {
    const key = `${position.position_label}:${position.player_group}`
    if (positionKeys.has(key)) {
      return 'Each position and player group row must be unique.'
    }
    positionKeys.add(key)
  }

  return ''
}
