import { Link } from 'react-router-dom'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import {
  ShieldCheckIcon,
  SoccerBallIcon,
} from '../../components/BrowseIcons.jsx'
import { AddressIcon, GameSpotsIcon, GameTimeIcon, GameTraitIcon } from '../../components/GameFactIcons.jsx'
import {
  formatEnvironment,
  formatGamePlayerGroup,
  formatPrice,
  formatTimeRange,
} from './myGamesFormatters.js'
import { buildMediaUrl } from '../../lib/apiClient.js'

function MyGameCard({ item }) {
  const { bucket, game } = item
  const statusLabel = item.statusLabel || item.status_label
  const statusTone = item.statusTone || item.status_tone
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const imageUrl = buildMediaUrl(game.primary_image_url)
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const participantCount = game.participant_count || 0
  const isFull = participantCount >= game.total_spots
  const isHistory = bucket === 'history'
  const locationLabel = [game.city_snapshot, game.state_snapshot].filter(Boolean).join(', ')
  const gameSpec = [
    formatGamePlayerGroup(game.game_player_group),
    game.format_label,
    formatEnvironment(game.environment_type),
  ].filter(Boolean).join(' · ')

  return (
    <Link
      className={`game-card game-card--${tone} ${
        isFull ? 'game-card--full' : ''
      } my-game-card my-game-card--${statusTone}`}
      to={`/games/${game.id}`}
    >
      <div className="game-card__media">
        <div className="game-card__fallback">
          <SoccerBallIcon />
        </div>

        {cardImageUrl && <img src={cardImageUrl} alt="" loading="lazy" />}

        <GameTypeBadge gameType={game.game_type} />
        {isFull && !isHistory && <span className="game-card__full-badge">Full</span>}
      </div>

      <div className="game-card__body">
        <div className="my-game-card__heading">
          <h3>{title}</h3>
          <span className={`my-game-card__status my-game-card__status--${statusTone}`}>
            {statusLabel}
          </span>
        </div>

        <p className="game-card__location">
          <AddressIcon />
          {locationLabel || 'Location not set'}
        </p>

        <p className="game-card__meta">
          <GameTimeIcon />
          {formatTimeRange(game.starts_at, game.ends_at)}
        </p>

        <p className="game-card__meta">
          <GameTraitIcon />
          <span className="game-card__meta-text">{gameSpec}</span>
        </p>
      </div>

      <div className="game-card__footer">
        <span>
          <GameSpotsIcon />
          <strong>
            {participantCount}/{game.total_spots}
          </strong>{' '}
          spots
        </span>

        <span>{formatPrice(game.price_per_player_cents, game.currency)}</span>
      </div>
    </Link>
  )
}

function GameTypeBadge({ gameType }) {
  const isCommunity = gameType === 'community'

  return (
    <span className={`game-card__badge game-card__badge--${gameType}`}>
      {isCommunity ? <SoccerBallIcon /> : <ShieldCheckIcon />}
      {isCommunity ? 'Community' : 'Official'}
    </span>
  )
}

export default MyGameCard
