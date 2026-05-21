import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  StopwatchIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  buildMapsUrl,
  formatDate,
  formatEnvironment,
  formatHeroLocation,
  formatPrice,
  formatTimeRange,
  formatVenueAddress,
  getDurationLabel,
} from './browseGameFormatters.js'
import {
  buildRuleItems,
  canUseGameChat,
  getJoinLabel,
  getVisibleHostPaymentMethods,
} from './gameDetailsSelectors.js'

const JOIN_WINDOW_MINUTES = 5

export function buildGameDetailsViewModel({
  communityGameDetails,
  currentGuestCount,
  currentParticipant,
  currentUser,
  game,
  isJoining,
  nowMs,
  participantSummary,
  participants,
  venue,
}) {
  const title = game.title || `${game.venue_name_snapshot || 'Pickup'} Game`
  const venueName = game.venue_name_snapshot || venue?.name || 'Pickup Lane'
  const city = game.city_snapshot || venue?.city || 'Chicago'
  const state = game.state_snapshot || venue?.state
  const heroLocation = formatHeroLocation(
    venueName,
    game.neighborhood_snapshot || venue?.neighborhood,
    city,
    state,
  )
  const isCancelledGame = game.game_status === 'cancelled'
  const gameToneLabel = isCancelledGame
    ? 'Cancelled'
    : game.game_type === 'community'
      ? 'Community Game'
      : 'Official Game'
  const dateLabel = formatDate(game.starts_at)
  const timeLabel = formatTimeRange(game.starts_at, game.ends_at)
  const durationLabel = getDurationLabel(game.starts_at, game.ends_at)
  const environmentLabel = formatEnvironment(game.environment_type)
  const price = formatPrice(game.price_per_player_cents, game.currency)
  const facts = [
    { icon: <CalendarIcon />, label: dateLabel },
    { icon: <ClockIcon />, label: timeLabel },
    { icon: <StopwatchIcon />, label: durationLabel },
    { icon: <BuildingIcon />, label: environmentLabel },
    { icon: <UsersIcon />, label: game.format_label || 'Pickup' },
  ]
  const venueAddress = formatVenueAddress(game, venue)
  const mapsUrl = buildMapsUrl(venue, venueAddress)
  const aboutText =
    game.description ||
    'Fast-paced pickup soccer. All skill levels welcome. Show up ready to play and have fun.'
  const hostPaymentMethods = getVisibleHostPaymentMethods(game, communityGameDetails)
  const parkingNote = game.parking_notes || ''
  const ruleItems = buildRuleItems(game)
  const scheduledStartMs = new Date(game.starts_at).getTime()
  const isGameStarted = nowMs !== null && nowMs >= scheduledStartMs
  const canShowEditGame =
    game.game_type === 'community' &&
    currentUser?.id === game.host_user_id &&
    game.publish_status === 'published' &&
    ['scheduled', 'full'].includes(game.game_status)
  const canEditGame = canShowEditGame && !isGameStarted
  const isHost = currentUser?.id && currentUser.id === game.host_user_id
  const canShowCancelGame =
    game.publish_status === 'published' &&
    ['scheduled', 'full'].includes(game.game_status) &&
    (
      currentUser?.role === 'admin' ||
      (game.game_type === 'community' && isHost)
    )
  const canCancelGame = canShowCancelGame && !isGameStarted
  const canOpenGameChat = canUseGameChat(game, participants, currentUser)
  const hostGuestMax = game.allow_guests ? game.host_guest_max || 0 : 0
  const hostGuestAddSlots = Math.max(
    Math.min(hostGuestMax - currentGuestCount, participantSummary.spotsLeft),
    0,
  )
  const isJoinWindowClosed =
    nowMs !== null &&
    nowMs >= scheduledStartMs + JOIN_WINDOW_MINUTES * 60 * 1000
  const isGameClosed =
    !['published'].includes(game.publish_status) ||
    !['scheduled', 'full'].includes(game.game_status) ||
    isJoinWindowClosed
  const playerGuestMax = game.allow_guests ? game.max_guests_per_booking || 0 : 0
  const isConfirmedPlayer =
    Boolean(currentParticipant) &&
    !isHost &&
    currentParticipant.participant_status === 'confirmed'
  const canShowBookingGuestAction = isConfirmedPlayer && playerGuestMax > 0
  const bookingGuestAddSlots = canShowBookingGuestAction
    ? Math.max(Math.min(playerGuestMax - currentGuestCount, participantSummary.spotsLeft), 0)
    : 0
  const canAddBookingGuests = canShowBookingGuestAction && !isGameClosed && bookingGuestAddSlots > 0
  const joinLabel = getJoinLabel({
    currentParticipant,
    gameStatus: game.game_status,
    isJoinWindowClosed,
    isCancelledGame,
    isGameClosed,
    isPublished: game.publish_status === 'published',
    isHost,
    isJoining,
    participantSummary,
    waitlistEnabled: game.waitlist_enabled,
  })
  const isJoinDisabled = Boolean(isHost || currentParticipant || isGameClosed || isJoining)
  const isClosedJoinStatus =
    isJoinDisabled && ['Cancelled', 'Completed', 'Join Closed', 'Game Closed'].includes(joinLabel)
  const mobileActionCount = [
    canShowEditGame,
    isHost && hostGuestMax > 0,
    currentParticipant && !isHost && !isJoinWindowClosed,
    canShowCancelGame,
    true,
  ].filter(Boolean).length

  return {
    aboutText,
    bookingGuestAddSlots,
    canAddBookingGuests,
    canCancelGame,
    canEditGame,
    canOpenGameChat,
    canShowCancelGame,
    canShowEditGame,
    facts,
    gameToneLabel,
    heroLocation,
    hostGuestAddSlots,
    hostGuestMax,
    hostPaymentMethods,
    isCancelledGame,
    isClosedJoinStatus,
    isGameClosed,
    isHost,
    isJoinDisabled,
    isJoinWindowClosed,
    joinLabel,
    mapsUrl,
    mobileActionCount,
    parkingNote,
    playerGuestMax,
    price,
    ruleItems,
    title,
    venueAddress,
    venueName,
  }
}
