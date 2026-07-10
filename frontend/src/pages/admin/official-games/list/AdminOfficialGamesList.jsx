import { Link } from 'react-router-dom'
import { Trophy } from 'lucide-react'
import {
  AddressIcon,
  GameDateIcon,
  GameSpotsIcon,
  GameTimeIcon,
  GameTraitIcon,
} from '../../../../components/GameFactIcons.jsx'
import {
  formatEnvironment,
  formatGamePlayerGroup,
} from '../../../browse-games/browseGameFormatters.js'
import { formatAdminGameMoney } from '../shared/adminOfficialGameForm.js'

const fallbackTimeZone = 'America/Chicago'

function formatDateLabel(dateValue) {
  if (dateValue) {
    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      weekday: 'short',
      year: 'numeric',
    }).format(new Date(`${dateValue}T12:00:00`))
  }

  return 'Date unavailable'
}

function formatGameDate(game) {
  if (game.starts_on_local) {
    return formatDateLabel(game.starts_on_local)
  }

  if (!game.starts_at) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    timeZone: game.timezone || fallbackTimeZone,
    weekday: 'short',
    year: 'numeric',
  }).format(new Date(game.starts_at))
}

function formatTimeRange(game) {
  if (!game.starts_at || !game.ends_at) {
    return 'Time unavailable'
  }

  const timeZone = game.timezone || fallbackTimeZone
  const formatter = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone,
  })

  return `${formatter.format(new Date(game.starts_at))} - ${formatter.format(new Date(game.ends_at))}`
}

function getLocationLine(game) {
  return [
    game.city_snapshot,
    game.state_snapshot,
  ].filter(Boolean).join(', ') || 'Location unavailable'
}

function getGameSpec(game) {
  return [
    formatGamePlayerGroup(game.game_player_group),
    game.format_label,
    formatEnvironment(game.environment_type),
  ].filter(Boolean).join(' · ')
}

function getCardTitle(game) {
  const title = String(game.title || '').trim()
  const formatLabel = String(game.format_label || '').trim()

  if (formatLabel && title.toLowerCase().endsWith(` ${formatLabel.toLowerCase()}`)) {
    return title.slice(0, -formatLabel.length).trim()
  }

  return title || 'Official Game'
}

function getDateGroupKey(game) {
  return game.starts_on_local || game.starts_at || 'unknown'
}

function groupGamesByDate(games) {
  const groups = []
  const groupsByKey = new Map()

  games.forEach((game) => {
    const key = getDateGroupKey(game)
    const label = game.starts_on_local
      ? formatDateLabel(game.starts_on_local)
      : formatGameDate(game)

    if (!groupsByKey.has(key)) {
      const group = {
        games: [],
        key,
        label,
      }
      groupsByKey.set(key, group)
      groups.push(group)
    }

    groupsByKey.get(key).games.push(game)
  })

  return groups
}

function getSpotsClass(game) {
  if (Number(game.booked_spots) >= Number(game.total_spots)) {
    return 'is-full'
  }

  return Number(game.booked_spots) > 0 ? 'has-bookings' : ''
}

function AdminOfficialGameThumbnail({ game }) {
  const hasMissingHost = game.issues?.includes('missing_host')

  if (game.primary_venue_image_url) {
    return (
      <div className="admin-official-game-card__thumb">
        <img alt="" src={game.primary_venue_image_url} />
        {hasMissingHost && <span className="admin-official-game-card__issue-badge">Missing host</span>}
      </div>
    )
  }

  return (
    <div className="admin-official-game-card__thumb admin-official-game-card__thumb--fallback" aria-hidden="true">
      <GameTraitIcon />
      {hasMissingHost && <span className="admin-official-game-card__issue-badge">Missing host</span>}
    </div>
  )
}

function AdminOfficialGameCard({ game }) {
  return (
    <Link className="admin-official-game-card" to={`/admin/official-games/${game.id}`}>
      <AdminOfficialGameThumbnail game={game} />

      <div className="admin-official-game-card__body">
        <h3>{getCardTitle(game)}</h3>
        <p>
          <AddressIcon />
          {getLocationLine(game)}
        </p>
        <p>
          <GameTimeIcon />
          {formatTimeRange(game)}
        </p>
        <p>
          <GameTraitIcon />
          {getGameSpec(game)}
        </p>
      </div>

      <div className="admin-official-game-card__footer">
        <span className={`admin-official-game-card__capacity ${getSpotsClass(game)}`.trim()}>
          <GameSpotsIcon />
          <span className="admin-official-game-card__capacity-copy">
            <strong>{game.booked_spots}/{game.total_spots}</strong> spots
          </span>
        </span>
        <span>{formatAdminGameMoney(game.price_per_player_cents, game.currency)}</span>
      </div>
    </Link>
  )
}

function AdminOfficialGamesList({ games, hasFilters = false }) {
  if (!games.length) {
    return (
      <div className="admin-official-empty-state">
        <Trophy aria-hidden="true" />
        <strong>No official games found</strong>
        <span>
          {hasFilters
            ? 'Try clearing the search, date, or changing views.'
            : 'Official games will appear here after they are created.'}
        </span>
      </div>
    )
  }

  const groupedGames = groupGamesByDate(games)

  return (
    <div className="admin-official-date-groups">
      {groupedGames.map((group) => (
        <section className="admin-official-date-group" key={group.key}>
          <div className="admin-official-date-group__header">
            <h3>
              <GameDateIcon />
              {group.label}
            </h3>
          </div>

          <div className="admin-official-card-grid">
            {group.games.map((game) => (
              <AdminOfficialGameCard game={game} key={game.id} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

export default AdminOfficialGamesList
