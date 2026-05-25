import { adminOfficialTimeOptions } from './adminCreateOfficialGameData.js'

export function buildAdminOfficialAddress(form) {
  const stateLine = [form.state.trim(), form.postalCode.trim()].filter(Boolean).join(' ')
  const cityLine = [form.city.trim(), stateLine].filter(Boolean).join(', ')
  return [form.addressLine1.trim(), cityLine].filter(Boolean).join(', ')
}

export function formatAdminOfficialDate(date) {
  if (!date) {
    return 'Date not set'
  }

  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(`${date}T12:00:00`))
}

export function formatAdminOfficialTime(value) {
  return adminOfficialTimeOptions.find((option) => option.value === value)?.label || value
}

export function formatAdminOfficialMoney(value) {
  const cents = Math.round((Number(value) || 0) * 100)
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(cents / 100)
}

export function buildAdminOfficialGeneratedTitle(form) {
  return `${form.venueName.trim() || 'Official'} ${form.formatLabel}`.trim()
}

export function formatAdminOfficialVenue(form) {
  return form.venueName || 'Venue not set'
}

export function getAdminOfficialReview(form) {
  return {
    date: formatAdminOfficialDate(form.date),
    time: `${formatAdminOfficialTime(form.startTime)} - ${formatAdminOfficialTime(form.endTime)}`,
    venue: formatAdminOfficialVenue(form),
    address: buildAdminOfficialAddress(form),
    price: formatAdminOfficialMoney(form.price),
  }
}
