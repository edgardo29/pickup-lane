import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import { buildMediaUrl } from '../../lib/apiClient.js'
import { formatVenueAddress } from './browseGameFormatters.js'
import {
  ACTIVE_JOIN_STATUSES,
  getCurrentGuestCount,
  getParticipantSummary,
} from './gameParticipantSelectors.js'

const JOIN_WINDOW_MINUTES = 5

export function buildGameCheckoutViewModel({
  agreed,
  appUser,
  game,
  guestCount,
  images,
  isAddGuestsCheckout,
  isSubmitting,
  nowMs,
  participants,
  paymentMethods,
  selectedPaymentMethodId,
  venue,
}) {
  const summary = getParticipantSummary(participants, game?.total_spots)
  const existingParticipant =
    participants.find(
      (participant) =>
        participant.user_id === appUser?.id &&
        ACTIVE_JOIN_STATUSES.has(participant.participant_status),
    ) || null
  const primaryImage = getPrimaryImage(images, game)
  const maxGuests = game?.allow_guests ? game.max_guests_per_booking || 0 : 0
  const currentGuestCount = getCurrentGuestCount(participants, existingParticipant, appUser?.id)
  const isPaymentResume = Boolean(
    !isAddGuestsCheckout && existingParticipant?.participant_status === 'pending_payment',
  )
  const addableGuestCount = isAddGuestsCheckout
    ? Math.max(Math.min(maxGuests - currentGuestCount, summary.spotsLeft), 0)
    : maxGuests
  const minGuestCount = isAddGuestsCheckout && addableGuestCount > 0 ? 1 : 0
  const maxSelectableGuests = Math.max(addableGuestCount, 0)
  const effectiveGuestCount = isPaymentResume
    ? currentGuestCount
    : Math.min(Math.max(guestCount, minGuestCount), maxSelectableGuests)
  const projectedGuestCount = isAddGuestsCheckout
    ? Math.min(currentGuestCount + effectiveGuestCount, maxGuests)
    : effectiveGuestCount
  const partySize = isAddGuestsCheckout ? effectiveGuestCount : effectiveGuestCount + 1
  const price = game?.price_per_player_cents || 0
  const platformFee = 0
  const total = price * partySize + platformFee
  const isJoinWindowClosed = game
    ? nowMs !== null &&
      nowMs >= new Date(game.starts_at).getTime() + JOIN_WINDOW_MINUTES * 60 * 1000
    : false
  const currentPendingPartySize = isPaymentResume ? currentGuestCount + 1 : 0
  const availableSpotsForCheckout = summary.spotsLeft + currentPendingPartySize
  const hasEnoughSpots = partySize <= availableSpotsForCheckout
  const isWaitlistCheckout = Boolean(!isAddGuestsCheckout && game && !hasEnoughSpots && game.waitlist_enabled)
  const isBlockedByCapacity = isAddGuestsCheckout
    ? effectiveGuestCount <= 0
    : Boolean(game && !hasEnoughSpots && !game.waitlist_enabled)
  const isAddGuestsBlockedByParticipant =
    isAddGuestsCheckout && existingParticipant?.participant_status !== 'confirmed'
  const title = game ? game.title || `${game.venue_name_snapshot} ${game.format_label}` : ''
  const address = game ? formatVenueAddress(game, venue, { avoidDuplicateLocality: true }) : ''
  const paymentMethod =
    paymentMethods.find((method) => method.id === selectedPaymentMethodId) ||
    paymentMethods.find((method) => method.is_default) ||
    paymentMethods[0] ||
    null
  const confirmLabel = getConfirmLabel({
    isAddGuestsCheckout,
    isBlockedByCapacity,
    isJoinWindowClosed,
    isSubmitting,
    isWaitlistCheckout,
  })

  return {
    address,
    confirmLabel,
    effectiveGuestCount,
    existingParticipant,
    isAddGuestsBlockedByParticipant,
    isBlockedByCapacity,
    isJoinWindowClosed,
    isPaymentResume,
    isWaitlistCheckout,
    maxGuests,
    maxSelectableGuests,
    minGuestCount,
    paymentMethod,
    paymentMethods,
    platformFee,
    price,
    primaryImage,
    projectedGuestCount,
    summary,
    title,
    total,
  }
}

function getConfirmLabel({
  isAddGuestsCheckout,
  isBlockedByCapacity,
  isJoinWindowClosed,
  isSubmitting,
  isWaitlistCheckout,
}) {
  if (isSubmitting) {
    return 'Confirming...'
  }

  if (isJoinWindowClosed) {
    return isAddGuestsCheckout ? 'Attendance Closed' : 'Join Closed'
  }

  if (isBlockedByCapacity) {
    return 'Not Enough Spots'
  }

  if (isAddGuestsCheckout) {
    return 'Confirm Guests'
  }

  return isWaitlistCheckout ? 'Join Waitlist' : 'Confirm Spot'
}

function getPrimaryImage(images, game) {
  const image = images
    .slice()
    .sort(
      (first, second) =>
        Number(second.is_primary) - Number(first.is_primary) ||
        first.sort_order - second.sort_order,
    )[0]

  if (image?.image_url) {
    return buildMediaUrl(image.image_url)
  }

  return game?.game_type === 'community' ? defaultCommunityVenueImage : defaultCommunityVenueImage
}
