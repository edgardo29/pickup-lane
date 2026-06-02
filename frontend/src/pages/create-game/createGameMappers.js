import { normalizeUsStateCode } from '../../data/usStates.js'
import { normalizePaymentMethods } from './createGamePayment.js'
import { toDateInputValue, toTimeInputValue } from './createGameSchedule.js'

export function mapGameToForm(game, venue, communityDetails = null) {
  const startsAt = new Date(game.starts_at)
  const endsAt = new Date(game.ends_at)

  return {
    date: toDateInputValue(startsAt),
    startTime: toTimeInputValue(startsAt),
    endTime: toTimeInputValue(endsAt),
    format: game.format_label || '7v7',
    gamePlayerGroup: game.game_player_group || 'coed',
    skillLevel: game.skill_level || 'any',
    environment: game.environment_type || 'outdoor',
    totalSpots: game.total_spots || 14,
    price: Math.round((game.price_per_player_cents || 0) / 100),
    venueName: venue?.name || game.venue_name_snapshot || '',
    street: venue?.address_line_1 || getStreetFromAddressSnapshot(game.address_snapshot),
    city: venue?.city || game.city_snapshot || '',
    state: normalizeUsStateCode(venue?.state || game.state_snapshot),
    zip: venue?.postal_code || '',
    neighborhood: venue?.neighborhood || game.neighborhood_snapshot || '',
    parkingNote: game.parking_notes || '',
    gameNotes: game.game_notes || '',
    hostRules: game.custom_rules_text || '',
    paymentMethods: normalizePaymentMethods(
      communityDetails?.payment_methods_snapshot,
    ),
  }
}

function getStreetFromAddressSnapshot(addressSnapshot) {
  return addressSnapshot?.split(',')[0]?.trim() || ''
}
