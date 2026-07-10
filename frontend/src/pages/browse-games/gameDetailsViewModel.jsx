import {
  GameDateIcon,
  GameDurationIcon,
  GameEnvironmentIcon,
  GameFormatIcon,
  GameIndoorIcon,
  GameOutdoorIcon,
  GamePlayerGroupIcon,
  GameSkillIcon,
  GameTimeIcon,
} from '../../components/GameFactIcons.jsx'
import {
  buildMapsUrl,
  formatDate,
  formatEnvironment,
  formatGamePlayerGroup,
  formatHeroLocation,
  formatPrice,
  formatSkillLevel,
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
  canAdminCancelCommunityGame = false,
  canAdminCancelOfficialGame = false,
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
    { includeVenue: false },
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
  const EnvironmentIcon =
    game.environment_type === 'outdoor'
      ? GameOutdoorIcon
      : game.environment_type === 'indoor'
        ? GameIndoorIcon
        : GameEnvironmentIcon
  const playerGroupLabel = formatGamePlayerGroup(game.game_player_group)
  const skillLevelLabel = formatSkillLevel(game.skill_level)
  const price = formatPrice(game.price_per_player_cents, game.currency)
  const facts = [
    { icon: <GameDateIcon />, label: dateLabel },
    { icon: <GameTimeIcon />, label: timeLabel },
    { icon: <GameDurationIcon />, label: durationLabel },
    { icon: <EnvironmentIcon />, label: environmentLabel },
    { icon: <GameFormatIcon />, label: game.format_label || 'Pickup' },
    { icon: <GamePlayerGroupIcon />, label: playerGroupLabel || 'Coed' },
    { icon: <GameSkillIcon />, label: skillLevelLabel || 'Any Skill' },
  ]
  const venueAddress = formatVenueAddress(game, venue, { avoidDuplicateLocality: true })
  const mapsUrl = buildMapsUrl(venue, venueAddress)
  const aboutText = typeof game.description === 'string' ? game.description.trim() : ''
  const hostRulesText = typeof game.custom_rules_text === 'string' ? game.custom_rules_text.trim() : ''
  const hostPaymentMethods = getVisibleHostPaymentMethods(game, communityGameDetails)
  const parkingNote = game.parking_notes || ''
  const ruleItems = buildRuleItems(game)
  const scheduledStartMs = new Date(game.starts_at).getTime()
  const isGameStarted = nowMs !== null && nowMs >= scheduledStartMs
  const canShowEditGame =
    game.game_type === 'community' &&
    currentUser?.id === game.host_user_id &&
    game.publish_status === 'published' &&
    game.game_status === 'active'
  const canEditGame = canShowEditGame && !isGameStarted
  const isHost = currentUser?.id && currentUser.id === game.host_user_id
  const canShowOfficialAdminCancel =
    game.game_type === 'official' && canAdminCancelOfficialGame
  const canShowCommunityCancel =
    game.game_type === 'community' && (isHost || canAdminCancelCommunityGame)
  const canShowCancelGame =
    game.publish_status === 'published' &&
    game.game_status === 'active' &&
    (
      canShowOfficialAdminCancel ||
      canShowCommunityCancel
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
    game.game_status !== 'active' ||
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
    cancelGameOpensAdminWorkflow: canShowOfficialAdminCancel,
    canShowCancelGame,
    canShowEditGame,
    facts,
    gameToneLabel,
    heroLocation,
    hostGuestAddSlots,
    hostGuestMax,
    hostPaymentMethods,
    hostRulesText,
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
