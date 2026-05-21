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
      text: isCommunityGame
        ? game.custom_cancellation_text ||
          'Check the host payment note before canceling. Pickup Lane does not process player refunds for community games.'
        : 'Cancel 24+ hours before game time for refund or game credit eligibility.',
    },
    {
      title: isCommunityGame ? 'If The Host Cancels' : 'If Pickup Lane Cancels',
      kind: 'shield',
      text: isCommunityGame
        ? 'The host should contact players with next steps for any off-app payments.'
        : 'Players receive a refund or game credit when Pickup Lane cancels an official game.',
    },
    {
      title: 'Signup Window',
      kind: 'clock',
      text: 'New signups close 5 minutes after the scheduled start time.',
    },
    {
      title: 'Waitlist',
      kind: 'players',
      text: 'Waitlisted players only pay if moved to the confirmed player list.',
    },
    {
      title: 'Weather',
      kind: 'weather',
      text: isOutdoorGame
        ? 'Outdoor games may be canceled for dangerous weather, including thunderstorms, lightning, or unsafe field conditions.'
        : 'Indoor games run unless the venue has an unexpected closure or unsafe condition.',
    },
    {
      title: 'Age Requirement',
      kind: 'age',
      text: `Players must be ${game.minimum_age || 18} years or older.`,
    },
  ]

  if (game.custom_rules_text) {
    rules.unshift({
      title: 'Game Rules',
      kind: 'rules',
      text: game.custom_rules_text,
    })
  }

  return rules
}
