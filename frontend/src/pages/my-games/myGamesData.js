const ACTIVE_PARTICIPANT_STATUSES = new Set(['pending_payment', 'confirmed'])
const UPCOMING_MY_GAME_STATUSES = new Set(['pending_payment', 'confirmed', 'waitlisted'])
const HISTORY_MY_GAME_STATUSES = new Set(['confirmed'])
const GAME_CANCELLED_TYPES = new Set(['host_cancelled', 'admin_cancelled'])
const UPCOMING_WINDOW_DAYS = 14

export function buildParticipantCounts(participants) {
  const counts = new Map()

  participants.forEach((participant) => {
    if (!ACTIVE_PARTICIPANT_STATUSES.has(participant.participant_status)) {
      return
    }

    counts.set(participant.game_id, (counts.get(participant.game_id) || 0) + 1)
  })

  return counts
}

export function buildMyGameItems(myParticipants, gamesById, currentUser, nowMs) {
  return myParticipants
    .map((participant) => {
      const game = gamesById.get(participant.game_id)

      if (!game || game.deleted_at || game.publish_status !== 'published') {
        return null
      }

      const isPast = new Date(game.ends_at).getTime() < nowMs || game.game_status === 'completed'
      const isCancelled = game.game_status === 'cancelled'
      const isHost = participant.participant_type === 'host' || game.host_user_id === currentUser?.id
      const bucket = getMyGameBucket(game, participant, isPast, isCancelled, isHost)

      if (!bucket) {
        return null
      }

      return {
        bucket,
        game,
        isHost,
        participant,
        ...getMyGameStatus(game, participant, isHost, bucket),
      }
    })
    .filter(Boolean)
    .sort((first, second) =>
      first.bucket === 'history'
        ? new Date(second.game.starts_at) - new Date(first.game.starts_at)
        : new Date(first.game.starts_at) - new Date(second.game.starts_at),
    )
}

export function getVisibleUpcomingItems(items, visibleWindowCount, nowMs) {
  const windowEnd = nowMs + visibleWindowCount * UPCOMING_WINDOW_DAYS * 24 * 60 * 60 * 1000

  return items.filter((item) => new Date(item.game.starts_at).getTime() <= windowEnd)
}

export function groupUpcomingAgendaItems(items) {
  const dateGroups = new Map()

  items.forEach((item) => {
    const dateKey = getDateKey(item.game.starts_at)

    if (!dateGroups.has(dateKey)) {
      dateGroups.set(dateKey, {
        key: dateKey,
        label: formatAgendaDate(item.game.starts_at),
        items: [],
      })
    }

    dateGroups.get(dateKey).items.push(item)
  })

  return [...dateGroups.values()]
}

export function groupHistoryAgendaItems(items) {
  const groups = items.reduce((groupMap, item) => {
    const key = getDateKey(item.game.starts_at)
    const label = formatAgendaDate(item.game.starts_at)

    if (!groupMap.has(key)) {
      groupMap.set(key, { key, label, items: [] })
    }

    groupMap.get(key).items.push(item)
    return groupMap
  }, new Map())

  return [...groups.values()]
}

export function formatTimeRange(start, end) {
  return `${formatStartTime(start)} - ${formatStartTime(end)}`
}

export function formatEnvironment(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ') : 'Pickup'
}

export function formatPrice(cents, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100)
}

function getMyGameBucket(game, participant, isPast, isCancelled, isHost) {
  if (isCancelled) {
    return isGameCancelledHistoryParticipant(participant, isHost) ? 'history' : null
  }

  if (isPast) {
    return isHistoricalParticipant(participant, isHost) ? 'history' : null
  }

  if (UPCOMING_MY_GAME_STATUSES.has(participant.participant_status) || isHost) {
    return 'upcoming'
  }

  return null
}

function isGameCancelledHistoryParticipant(participant, isHost) {
  if (UPCOMING_MY_GAME_STATUSES.has(participant.participant_status) || isHost) {
    return true
  }

  return (
    participant.participant_status === 'cancelled' &&
    GAME_CANCELLED_TYPES.has(participant.cancellation_type)
  )
}

function isHistoricalParticipant(participant, isHost) {
  return HISTORY_MY_GAME_STATUSES.has(participant.participant_status) || isHost
}

function getMyGameStatus(game, participant, isHost, bucket) {
  if (game.game_status === 'cancelled') {
    return { statusLabel: 'Cancelled', statusTone: 'cancelled' }
  }

  if (bucket === 'history') {
    return {
      statusLabel: isHost ? 'Hosted' : 'Played',
      statusTone: isHost ? 'hosted' : 'played',
    }
  }

  if (participant.participant_status === 'waitlisted') {
    return { statusLabel: 'Waitlisted', statusTone: 'waitlisted' }
  }

  if (isHost) {
    return { statusLabel: 'Hosting', statusTone: 'hosting' }
  }

  return { statusLabel: 'Confirmed', statusTone: 'confirmed' }
}

function getDateKey(value) {
  const date = new Date(value)
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

function formatAgendaDate(value) {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
    .format(new Date(value))
    .toUpperCase()
}

function formatStartTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}
