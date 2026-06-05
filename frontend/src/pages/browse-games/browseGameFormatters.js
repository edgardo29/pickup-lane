export function formatDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(value))
}

export function formatTime(value) {
  if (!value) {
    return ''
  }

  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export function formatTimeRange(start, end, { separator = '-' } = {}) {
  if (!start || !end) {
    return ''
  }

  return `${formatTime(start)}${separator}${formatTime(end)}`
}

export function getDurationLabel(start, end) {
  if (!start || !end) {
    return '60 min'
  }

  const minutes = Math.round((new Date(end) - new Date(start)) / 60000)
  return `${minutes || 60} min`
}

export function formatEnvironment(value) {
  if (!value) {
    return 'Pickup'
  }

  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ')
}

export function formatGamePlayerGroup(value) {
  const labels = {
    coed: 'Coed',
    men: 'Men',
    women: 'Women',
  }

  return labels[value] || (value ? formatEnvironment(value) : '')
}

export function formatSkillLevel(value) {
  const labels = {
    any: 'Any Skill',
    beginner: 'Beginner',
    recreational: 'Recreational',
    intermediate: 'Intermediate',
    advanced: 'Advanced',
    competitive: 'Competitive',
  }

  return labels[value] || (value ? formatEnvironment(value) : '')
}

export function formatPrice(cents, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100)
}

export function formatMoney(cents, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format((cents || 0) / 100)
}

export function formatVenueAddress(game, venue, { avoidDuplicateLocality = false } = {}) {
  const street = game.address_snapshot || venue?.address_line_1
  const city = game.city_snapshot || venue?.city
  const state = game.state_snapshot || venue?.state
  const postalCode = venue?.postal_code

  if (avoidDuplicateLocality && street && addressIncludesLocality(street, city, state, postalCode)) {
    return street
  }

  return [street, [city, state, postalCode].filter(Boolean).join(' ')].filter(Boolean).join(', ')
}

export function formatHeroLocation(venueName, neighborhood, city, state, { includeVenue = true } = {}) {
  const placeParts = []

  if (neighborhood && neighborhood !== city) {
    placeParts.push(neighborhood)
  }

  if (city) {
    placeParts.push(state ? `${city}, ${state}` : city)
  }

  return [includeVenue ? venueName : '', placeParts.join(', ')].filter(Boolean).join(' – ')
}

export function buildMapsUrl(venue, address) {
  const latitude = Number(venue?.latitude)
  const longitude = Number(venue?.longitude)

  if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
    return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`
  }

  if (address) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
  }

  return ''
}

export function formatPaymentMethod(paymentMethod) {
  if (!paymentMethod) {
    return 'Card details needed'
  }

  return `${capitalize(paymentMethod.card_brand || 'card')} ending ${paymentMethod.card_last4}`
}

function addressIncludesLocality(address, city, state, postalCode) {
  const normalizedAddress = address.toLowerCase()

  return [city, state, postalCode]
    .filter(Boolean)
    .some((addressPart) => normalizedAddress.includes(String(addressPart).toLowerCase()))
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}
