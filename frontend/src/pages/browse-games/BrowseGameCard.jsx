import { Link } from 'react-router-dom'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import {
  ClockIcon,
  MapPinIcon,
  ShieldCheckIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  formatEnvironment,
  formatPrice,
  formatTimeRange,
} from './browseGameFormatters.js'

function BrowseGameCard({ game, imageUrl, signedUpCount }) {
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const isFull = signedUpCount >= game.total_spots

  return (
    <Link className={`game-card game-card--${tone} ${isFull ? 'game-card--full' : ''}`} to={`/games/${game.id}`}>
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
          <MapPinIcon />
          {game.city_snapshot}
        </p>

        <p className="game-card__meta">
          <ClockIcon />
          {formatTimeRange(game.starts_at, game.ends_at, { separator: ' - ' })}
        </p>

        <p className="game-card__meta">
          <SoccerBallIcon />
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

export default BrowseGameCard
