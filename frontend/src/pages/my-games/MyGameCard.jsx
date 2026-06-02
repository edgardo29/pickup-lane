import { Link } from 'react-router-dom'
import defaultCommunityVenueImage from '../../assets/community-default/default-venue-wide.png'
import {
  ShieldCheckIcon,
  SoccerBallIcon,
} from '../../components/BrowseIcons.jsx'
import { AddressIcon, GameFormatIcon, GameSpotsIcon, GameTimeIcon } from '../../components/GameFactIcons.jsx'
import {
  formatEnvironment,
  formatGamePlayerGroup,
  formatPrice,
  formatSkillLevel,
  formatTimeRange,
} from './myGamesFormatters.js'

function MyGameCard({ imageUrl, item, participantCount }) {
  const { bucket, game, statusLabel, statusTone } = item
  const tone = game.game_type === 'community' ? 'community' : 'official'
  const title = game.venue_name_snapshot || game.title
  const cardImageUrl = imageUrl || (tone === 'community' ? defaultCommunityVenueImage : '')
  const isFull = participantCount >= game.total_spots
  const isHistory = bucket === 'history'
  const gameSpec = [
    formatEnvironment(game.environment_type),
    game.format_label,
    formatGamePlayerGroup(game.game_player_group),
    formatSkillLevel(game.skill_level),
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
          {game.city_snapshot}
        </p>

        <p className="game-card__meta">
          <GameTimeIcon />
          {formatTimeRange(game.starts_at, game.ends_at)}
        </p>

        <p className="game-card__meta">
          <GameFormatIcon />
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
