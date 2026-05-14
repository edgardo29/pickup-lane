import { Link } from 'react-router-dom'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import {
  MapPinIcon,
  ShieldCheckIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'

function BrowseGameCard({ game, imageUrl, signedUpCount }) {
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')

  return (
    <Link className={`game-card game-card--${tone}`} to={`/games/${game.id}`}>
      <div className="game-card__media">
        <div className="game-card__fallback">
          <SoccerBallIcon />
        </div>

        {cardImageUrl && <img src={cardImageUrl} alt="" loading="lazy" />}

        <span className="game-card__time">{formatStartTime(game.starts_at)}</span>

        <span className={`game-card__badge game-card__badge--${tone}`}>
          {tone === 'community' ? <SoccerBallIcon /> : <ShieldCheckIcon />}
          {tone === 'community' ? 'Community' : 'Official'}
        </span>
      </div>

      <div className="game-card__body">
        <h3>{title}</h3>

        <p className="game-card__location">
          <MapPinIcon />
          {game.neighborhood_snapshot || game.city_snapshot}
        </p>

        <p className="game-card__meta">
          {formatEnvironment(game.environment_type)}
          <span aria-hidden="true">•</span>
          {game.format_label}
        </p>
      </div>

      <div className="game-card__footer">
        <span>
          <UsersIcon />
          <strong>
            {signedUpCount}/{game.total_spots}
          </strong>{' '}
          spots
        </span>

        <span>{formatPrice(game.price_per_player_cents, game.currency)}</span>
      </div>
    </Link>
  )
}

function formatEnvironment(value) {
  if (!value) {
    return 'Pickup'
  }

  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll('_', ' ')
}

function formatPrice(cents, currency) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100)
}

function formatStartTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export default BrowseGameCard
