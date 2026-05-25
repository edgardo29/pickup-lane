function cleanText(value) {
  return String(value ?? '').trim()
}

function moneyToCents(value) {
  const normalized = String(value ?? '').replace(/[^\d.]/g, '')
  return Math.round((Number(normalized) || 0) * 100)
}

function buildIsoDateTime(date, time) {
  return new Date(`${date}T${time}:00`).toISOString()
}

function buildGeneratedTitle(form) {
  return `${cleanText(form.venueName) || 'Official'} ${form.formatLabel}`.trim()
}

export function buildAdminCreateOfficialGamePayload(form) {
  const payload = {
    title: buildGeneratedTitle(form),
    starts_at: buildIsoDateTime(form.date, form.startTime),
    ends_at: buildIsoDateTime(form.date, form.endTime),
    timezone: cleanText(form.timezone) || 'America/Chicago',
    format_label: form.formatLabel,
    environment_type: form.environmentType,
    total_spots: Number(form.totalSpots),
    price_per_player_cents: moneyToCents(form.price),
    allow_guests: Boolean(form.allowGuests),
    max_guests_per_booking: Number(form.maxGuestsPerBooking),
    waitlist_enabled: Boolean(form.waitlistEnabled),
    is_chat_enabled: Boolean(form.isChatEnabled),
    game_notes: null,
    parking_notes: cleanText(form.parkingNotes) || null,
    venue: {
      name: cleanText(form.venueName),
      address_line_1: cleanText(form.addressLine1),
      city: cleanText(form.city),
      state: cleanText(form.state),
      postal_code: cleanText(form.postalCode),
      country_code: cleanText(form.countryCode) || 'US',
      neighborhood: cleanText(form.neighborhood) || null,
    },
  }

  Object.keys(payload).forEach((key) => {
    if (payload[key] === undefined) {
      delete payload[key]
    }
  })

  return payload
}
