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
} from './browseGameFormatters.js'

function BrowseGameCard({ game, imageUrl, signedUpCount }) {
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const isFull = signedUpCount >= game.total_spots
  const gameSpec = [
    formatEnvironment(game.environment_type),
    game.format_label,
    formatGamePlayerGroup(game.game_player_group),
  ].filter(Boolean).join(' · ')

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
          <AddressIcon />
          {game.city_snapshot}
        </p>

        <p className="game-card__meta">
          <GameTimeIcon />
          {formatTimeRange(game.starts_at, game.ends_at, { separator: ' - ' })}
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
