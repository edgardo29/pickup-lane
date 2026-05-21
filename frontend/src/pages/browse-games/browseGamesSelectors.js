import { buildMediaUrl } from '../../lib/apiClient.js'
import { ACTIVE_ROSTER_STATUSES } from './gameParticipantSelectors.js'
import {
  BROWSE_VISIBLE_AFTER_START_MINUTES,
  DATE_WINDOW_DAYS,
} from './browseGamesData.js'

export function buildDateOptions(nowMs) {
  const startDate = new Date(nowMs)
  startDate.setHours(12, 0, 0, 0)

  return Array.from({ length: DATE_WINDOW_DAYS }, (_, index) => {
    const date = new Date(startDate)
    date.setDate(startDate.getDate() + index)

    return {
      key: getDateKey(date),
      weekday: new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date).toUpperCase(),
      month: new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date),
      day: new Intl.DateTimeFormat('en-US', { day: 'numeric' }).format(date),
    }
  })
}

export function buildImageUrlsByGameId(gameImages) {
  const images = new Map()

  gameImages.forEach((image) => {
    if (!images.has(image.game_id)) {
      images.set(image.game_id, buildMediaUrl(image.image_url))
    }
  })

  return images
}

export function buildParticipantCountsByGameId(participants) {
  const counts = new Map()

  participants.forEach((participant) => {
    if (!ACTIVE_ROSTER_STATUSES.has(participant.participant_status)) {
      return
    }

    counts.set(participant.game_id, (counts.get(participant.game_id) || 0) + 1)
  })

  return counts
}

export function getDateKey(value) {
  const date = new Date(value)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

export function getVisibleGames(games, nowMs) {
  const upcomingGames = games
    .filter(
      (game) => {
        const browseVisibleUntil =
          new Date(game.starts_at).getTime() + BROWSE_VISIBLE_AFTER_START_MINUTES * 60 * 1000

        return (
          !game.deleted_at &&
          game.game_status !== 'cancelled' &&
          browseVisibleUntil > nowMs
        )
      },
    )
    .sort((first, second) => new Date(first.starts_at) - new Date(second.starts_at))

  const publishedGames = upcomingGames.filter((game) => game.publish_status === 'published')

  return publishedGames.length > 0 ? publishedGames : upcomingGames
}

export function groupGamesByHour(games) {
  const groupedGames = games.reduce((groups, game) => {
    const date = new Date(game.starts_at)
    const label = new Intl.DateTimeFormat('en-US', { hour: 'numeric' }).format(date)

    if (!groups.has(label)) {
      groups.set(label, [])
    }

    groups.get(label).push(game)
    return groups
  }, new Map())

  return [...groupedGames.entries()].map(([label, groupGames]) => ({
    label,
    games: groupGames,
  }))
}
