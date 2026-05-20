import { toDateInputValue } from './needASubData.js'

export function buildNeedASubPayload(form, totalSpotsNeeded) {
  return {
    sport_type: 'soccer',
    format_label: form.formatLabel,
    environment_type: form.environment,
    skill_level: form.skillLevel,
    game_player_group: form.gamePlayerGroup,
    team_name: null,
    starts_at: new Date(`${form.date}T${form.startTime}:00`).toISOString(),
    ends_at: new Date(`${form.date}T${form.endTime}:00`).toISOString(),
    timezone: 'America/Chicago',
    location_name: form.locationName.trim(),
    address_line_1: form.addressLine1.trim(),
    city: form.city.trim(),
    state: form.state.trim().toUpperCase(),
    postal_code: form.postalCode.trim(),
    country_code: 'US',
    neighborhood: form.neighborhood.trim() || null,
    subs_needed: totalSpotsNeeded,
    price_due_at_venue_cents: getPriceDueCents(form.priceDue),
    currency: 'USD',
    payment_note: null,
    notes: form.notes.trim() || null,
    positions: form.positions.map((position, index) => ({
      position_label: position.position_label,
      player_group: position.player_group,
      spots_needed: Number(position.spots_needed),
      sort_order: index,
    })),
  }
}

export function hydrateNeedASubForm(post) {
  return {
    date: toDateInputValue(new Date(post.starts_at)),
    startTime: toTimeInputValue(new Date(post.starts_at)),
    endTime: toTimeInputValue(new Date(post.ends_at)),
    formatLabel: post.format_label,
    environment: post.environment_type || '',
    skillLevel: post.skill_level,
    gamePlayerGroup: post.game_player_group,
    locationName: post.location_name || '',
    addressLine1: post.address_line_1 || '',
    city: post.city || '',
    state: String(post.state || '').toUpperCase(),
    postalCode: post.postal_code || '',
    neighborhood: post.neighborhood || '',
    priceDue: formatHydratedPrice(post.price_due_at_venue_cents),
    notes: post.notes || '',
    positions: (post.positions || []).map((position, index) => ({
      position_label: position.position_label,
      player_group: position.player_group,
      spots_needed: position.spots_needed,
      sort_order: index,
    })),
  }
}

function getPriceDueCents(value) {
  const amount = Number(String(value || '').trim() || 0)
  if (!Number.isFinite(amount)) {
    return 0
  }

  return Math.max(0, Math.round(amount * 100))
}

function formatHydratedPrice(cents) {
  const amount = Number(cents || 0) / 100
  if (amount <= 0) {
    return ''
  }

  return Number.isInteger(amount) ? String(amount) : String(amount.toFixed(2))
}

function toTimeInputValue(date) {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
