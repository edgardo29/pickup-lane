import { normalizeUsStateCode } from '../../data/usStates.js'
import {
  getPriceCents,
  serializePaymentMethods,
} from './createGamePayment.js'
import { buildDateTime } from './createGameSchedule.js'

export function buildCommunityPublishPayload(form, currentUser, paymentMethod) {
  return {
    host_user_id: currentUser.id,
    starts_at: buildDateTime(form.date, form.startTime),
    ends_at: buildDateTime(form.date, form.endTime),
    timezone: 'America/Chicago',
    format_label: form.format,
    game_player_group: form.gamePlayerGroup,
    skill_level: form.skillLevel,
    environment_type: form.environment,
    total_spots: Number(form.totalSpots),
    price_per_player_cents: getPriceCents(form),
    venue: {
      name: form.venueName.trim(),
      address_line_1: form.street.trim(),
      city: form.city.trim(),
      state: normalizeUsStateCode(form.state) || form.state.trim().toUpperCase(),
      postal_code: form.zip.trim(),
      country_code: 'US',
      neighborhood: form.neighborhood.trim() || null,
    },
    payment_methods_snapshot: serializePaymentMethods(form.paymentMethods),
    payment_instructions_snapshot: null,
    custom_rules_text: (form.hostRules || '').trim() || null,
    game_notes: form.gameNotes.trim() || null,
    parking_notes: form.parkingNote.trim() || null,
    payment_method_id: paymentMethod?.id || null,
  }
}

export function buildHostEditPayload(form, currentUser) {
  return {
    acting_user_id: currentUser.id,
    starts_at: buildDateTime(form.date, form.startTime),
    ends_at: buildDateTime(form.date, form.endTime),
    format_label: form.format,
    game_player_group: form.gamePlayerGroup,
    skill_level: form.skillLevel,
    environment_type: form.environment,
    total_spots: Number(form.totalSpots),
    price_per_player_cents: getPriceCents(form),
    venue_name: form.venueName.trim(),
    address_line_1: form.street.trim(),
    city: form.city.trim(),
    state: normalizeUsStateCode(form.state) || form.state.trim().toUpperCase(),
    postal_code: form.zip.trim(),
    neighborhood: form.neighborhood.trim() || null,
    custom_rules_text: (form.hostRules || '').trim() || null,
    game_notes: form.gameNotes.trim() || null,
    parking_notes: form.parkingNote.trim() || null,
  }
}

export function buildCommunityGameDetailPayload(form, gameId) {
  return {
    game_id: gameId,
    payment_methods_snapshot: serializePaymentMethods(form.paymentMethods),
    payment_instructions_snapshot: null,
  }
}
