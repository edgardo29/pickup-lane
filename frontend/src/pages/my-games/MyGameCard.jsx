import { Link } from 'react-router-dom'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import {
  ClockIcon,
  MapPinIcon,
  ShieldCheckIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import { formatEnvironment, formatPrice, formatTimeRange } from './myGamesFormatters.js'

function MyGameCard({ imageUrl, item, participantCount }) {
  const { bucket, game, statusLabel, statusTone } = item
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const isFull = participantCount >= game.total_spots
  const isHistory = bucket === 'history'

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
          <MapPinIcon />
          {game.city_snapshot}
        </p>

        <p className="game-card__meta">
          <ClockIcon />
          {formatTimeRange(game.starts_at, game.ends_at)}
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
