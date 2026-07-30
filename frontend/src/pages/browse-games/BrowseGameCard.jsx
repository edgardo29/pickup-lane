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
  formatTimeRange,
} from './browseGameFormatters.js'
import { buildMediaUrl } from '../../lib/apiClient.js'

function BrowseGameCard({ animationIndex = 0, browseTimezone, game }) {
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.display_title || game.venue_name_snapshot || game.title
  const availability = game.availability || {}
  const signedUpCount = availability.occupied_spots ?? game.participant_count ?? 0
  const totalSpots = availability.total_spots ?? game.total_spots
  const occupiedSpotCount = Number(signedUpCount)
  const totalSpotCount = Number(totalSpots)
  const hasSpotCounts = Number.isFinite(occupiedSpotCount) && Number.isFinite(totalSpotCount)
  const isFull = hasSpotCounts && totalSpotCount > 0 && occupiedSpotCount >= totalSpotCount
  const imageUrl = buildMediaUrl(game.primary_image_url)
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const locationLabel = game.location_label || [game.city_snapshot, game.state_snapshot].filter(Boolean).join(', ')
  const cardClassName = `game-card game-card--${tone} pl-motion-enter`
  const motionDelay = `${36 + Math.min(animationIndex, 5) * 32}ms`
  const gameSpec = [
    formatGamePlayerGroup(game.game_player_group),
    game.format_label,
    formatEnvironment(game.environment_type),
  ].filter(Boolean).join(' · ')

  return (
    <Link
      className={cardClassName}
      style={{ '--pl-motion-delay': motionDelay }}
      to={`/games/${game.id}`}
    >
      <div className="game-card__media">
        <div className="game-card__fallback">
          <SoccerBallIcon />
        </div>

        {cardImageUrl && <img src={cardImageUrl} alt="" loading="lazy" />}

        <span className={`game-card__badge game-card__badge--${tone}`}>
          {tone === 'community' ? <SoccerBallIcon /> : <ShieldCheckIcon />}
          {tone === 'community' ? 'Community' : 'Official'}
        </span>
        {isFull && <span className="game-card__full-badge">Full</span>}
      </div>

      <div className="game-card__body">
        <h3>{title}</h3>

        <p className="game-card__location">
          <AddressIcon />
          {locationLabel || 'Location not set'}
        </p>

        <p className="game-card__meta">
          <GameTimeIcon />
          {formatTimeRange(game.starts_at, game.ends_at, { separator: ' - ', timeZone: browseTimezone })}
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
            {signedUpCount}/{totalSpots}
          </strong>{' '}
          spots
        </span>

        <span>{game.price_label}</span>
      </div>
    </Link>
  )
}

export default BrowseGameCard
