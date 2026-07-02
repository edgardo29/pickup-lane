import { LEGAL_POLICY_IDS } from '../../features/legal/legalPolicies.js'

export function canUseGameChat(game, participants, user) {
  if (!game?.is_chat_enabled || !user?.id) {
    return false
  }

  if (!['scheduled', 'full'].includes(game.game_status)) {
    return false
  }

  if (game.host_user_id === user.id) {
    return true
  }

  return participants.some(
    (participant) =>
      participant.user_id === user.id &&
      participant.participant_status === 'confirmed' &&
      ['registered_user', 'host', 'admin_added'].includes(participant.participant_type),
  )
}

export function getVisibleHostPaymentMethods(game, communityGameDetails) {
  if (
    game?.game_type !== 'community' ||
    game?.payment_collection_type !== 'external_host'
  ) {
    return []
  }

  if (communityGameDetails?.payment_text_moderation_status === 'hidden') {
    return []
  }

  return (communityGameDetails?.payment_methods_snapshot || [])
    .filter((method) => method?.type && method.type !== 'none' && method?.value)
    .map((method) => ({
      type: String(method.type).trim(),
      value: String(method.value).trim(),
    }))
}

export function getJoinLabel({
  currentParticipant,
  gameStatus,
  isJoinWindowClosed,
  isCancelledGame,
  isGameClosed,
  isPublished,
  isHost,
  isJoining,
  participantSummary,
  waitlistEnabled,
}) {
  if (isJoining) {
    return 'Joining...'
  }

  if (isCancelledGame) {
    return 'Cancelled'
  }

  if (isHost) {
    return 'Hosting'
  }

  if (currentParticipant?.participant_status === 'waitlisted') {
    return 'Waitlisted'
  }

  if (currentParticipant) {
    return 'Joined'
  }

  if (isGameClosed) {
    if (!isPublished) {
      return 'Game Closed'
    }

    if (gameStatus === 'completed') {
      return 'Completed'
    }

    if (isJoinWindowClosed) {
      return 'Join Closed'
    }

    return 'Game Closed'
  }

  if (participantSummary.spotsLeft <= 0 && waitlistEnabled) {
    return 'Join Waitlist'
  }

  return 'Join Game'
}

export function buildRuleItems(game) {
  const isCommunityGame = game.game_type === 'community'
  const isOutdoorGame = game.environment_type === 'outdoor'
  const rules = [
    {
      title: 'Canceling Your Spot',
      kind: 'clock',
      actionLabel: 'View full policy',
      policyId: LEGAL_POLICY_IDS.cancellationRefunds,
      text: isCommunityGame
        ? game.custom_cancellation_text ||
          'Review the host payment note before canceling. Pickup Lane does not refund off-app payments.'
        : 'Cancel 24+ hours before game time to stay eligible for a refund or game credit.',
    },
    {
      title: isCommunityGame ? 'If The Host Cancels' : 'If Pickup Lane Cancels',
      kind: 'shield',
      text: isCommunityGame
        ? 'The host manages updates and next steps for off-app payments.'
        : 'Players receive a refund or game credit for official games.',
    },
    {
      title: 'Signup Window',
      kind: 'clock',
      text: 'Signups close 5 minutes after start time. After that, the roster is locked.',
    },
    {
      title: 'Waitlist',
      kind: 'players',
      text: "Waitlisted players only pay if confirmed. You'll move up automatically when a spot opens.",
    },
    {
      title: 'Code of Conduct',
      kind: 'conduct',
      actionLabel: 'Read code of conduct',
      policyId: LEGAL_POLICY_IDS.codeOfConduct,
      text: 'Respect players, hosts, venues, and posted rules. Serious issues can affect your spot or account.',
    },
    {
      title: 'Weather',
      kind: 'weather',
      text: isOutdoorGame
        ? 'Outdoor games may be delayed or canceled for unsafe weather or field conditions.'
        : 'Indoor games run unless the venue closes or conditions become unsafe.',
    },
    {
      title: 'Age Requirement',
      kind: 'age',
      text: `Players must be ${game.minimum_age || 18} years or older to play. Age rules apply to every rostered player.`,
    },
  ]

  return rules
}
