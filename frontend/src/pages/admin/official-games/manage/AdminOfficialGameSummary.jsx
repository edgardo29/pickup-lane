import {
  GameDateIcon,
  GameDurationIcon,
  GameEnvironmentIcon,
  GameFormatIcon,
  GameIndoorIcon,
  GameOutdoorIcon,
  GamePlayerGroupIcon,
  GameSkillIcon,
  GameSpotsIcon,
  GameTimeIcon,
  PriceIcon,
  VenueIcon,
} from '../../../../components/GameFactIcons.jsx'
import {
  formatDate,
  formatEnvironment,
  formatGamePlayerGroup,
  formatPrice,
  formatSkillLevel,
  formatTimeRange,
  getDurationLabel,
} from '../../../browse-games/browseGameFormatters.js'

const activeRosterStatuses = new Set(['confirmed', 'pending_payment'])

function SummaryItem({ children, icon, label }) {
  return (
    <div className="admin-manage-summary__item">
      {icon}
      <span className="admin-manage-summary__copy">
        <small>{label}</small>
        <span className="admin-manage-summary__value">{children}</span>
      </span>
    </div>
  )
}

function AdminOfficialGameSummary({ game, participants }) {
  const EnvironmentIcon =
    game.environment_type === 'outdoor'
      ? GameOutdoorIcon
      : game.environment_type === 'indoor'
        ? GameIndoorIcon
        : GameEnvironmentIcon
  const price = formatPrice(game.price_per_player_cents, game.currency)
  const activeCount = participants.filter((participant) =>
    activeRosterStatuses.has(participant.participant_status),
  ).length

  return (
    <section className="admin-manage-summary" aria-label="Official game summary">
      <div className="admin-manage-summary__header">
        <div className="admin-manage-summary__identity">
          <span>Official game</span>
          <h2>{game.title}</h2>
        </div>
      </div>

      <div className="admin-manage-summary__grid">
        <SummaryItem icon={<GameDateIcon />} label="Date">
          {formatDate(game.starts_at)}
        </SummaryItem>
        <SummaryItem icon={<GameTimeIcon />} label="Time">
          {formatTimeRange(game.starts_at, game.ends_at)}
        </SummaryItem>
        <SummaryItem icon={<GameDurationIcon />} label="Duration">
          {getDurationLabel(game.starts_at, game.ends_at)}
        </SummaryItem>
        <SummaryItem icon={<EnvironmentIcon />} label="Environment">
          {formatEnvironment(game.environment_type)}
        </SummaryItem>
        <SummaryItem icon={<GameFormatIcon />} label="Format">
          {game.format_label || 'Pickup'}
        </SummaryItem>
        <SummaryItem icon={<GamePlayerGroupIcon />} label="Player group">
          {formatGamePlayerGroup(game.game_player_group) || 'Coed'}
        </SummaryItem>
        <SummaryItem icon={<GameSkillIcon />} label="Skill">
          {formatSkillLevel(game.skill_level) || 'Any Skill'}
        </SummaryItem>
        <SummaryItem icon={<PriceIcon />} label="Price">
          <><strong>{price}</strong> per player</>
        </SummaryItem>
        <SummaryItem icon={<GameSpotsIcon />} label="Roster">
          {activeCount} / {game.total_spots}
        </SummaryItem>
        <SummaryItem icon={<VenueIcon />} label="Venue">
          {game.venue_name_snapshot || 'Venue unavailable'}
        </SummaryItem>
      </div>
    </section>
  )
}

export default AdminOfficialGameSummary
