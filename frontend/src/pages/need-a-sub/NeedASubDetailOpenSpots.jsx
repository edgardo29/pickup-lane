import {
  NeedSubFieldPlayersIcon,
  NeedSubGoalkeeperIcon,
} from '../../components/GameFactIcons.jsx'
import { formatPositionLabel } from './needASubFormatters.js'
import { countHeldSpots } from './needASubSelectors.js'

const OPEN_SPOT_GROUPS = [
  {
    icon: NeedSubFieldPlayersIcon,
    label: 'Field Players',
    positionLabel: 'field_player',
  },
  {
    icon: NeedSubGoalkeeperIcon,
    label: 'Goalkeepers',
    positionLabel: 'goalkeeper',
  },
]

const PLAYER_GROUP_LABELS = {
  open: 'Any',
  men: 'Men',
  women: 'Women',
}

export function NeedASubDetailOpenSpots({
  canSelectSpot,
  onSelectPosition,
  post,
  selectedPositionId,
}) {
  const groups = OPEN_SPOT_GROUPS.map((group) => ({
    ...group,
    positions: (post.positions || [])
      .filter((position) => position.position_label === group.positionLabel)
      .sort((a, b) => getPlayerGroupOrder(a.player_group) - getPlayerGroupOrder(b.player_group)),
  }))
  const totalOpenCount = groups.reduce(
    (sum, group) => sum + group.positions.reduce(
      (groupSum, position) => groupSum + getPositionSpotsLeft(position),
      0,
    ),
    0,
  )

  return (
    <section className="need-sub-detail-section need-sub-detail-open-spots">
      <div className="need-sub-action-card-header need-sub-detail-open-spots__header">
        <p>Open Spots ({totalOpenCount})</p>
      </div>

      <div className="need-sub-detail-open-grid">
        {groups.map((group) => (
          <div className="need-sub-detail-open-group" key={group.positionLabel}>
            <div className="need-sub-detail-open-group__header">
              <group.icon />
              <div>
                <h3>{group.label}</h3>
              </div>
            </div>

            {group.positions.length ? (
              <div className="need-sub-detail-open-rows">
                {group.positions.map((position) => (
                  <OpenSpotRow
                    canSelectSpot={canSelectSpot}
                    isSelected={selectedPositionId === position.id}
                    key={position.id || `${position.position_label}-${position.player_group}`}
                    position={position}
                    onSelect={() => onSelectPosition(position.id)}
                  />
                ))}
              </div>
            ) : (
              <p className="need-sub-detail-empty-column">None requested</p>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

function OpenSpotRow({ canSelectSpot, isSelected, onSelect, position }) {
  const spotsLeft = getPositionSpotsLeft(position)
  const className = [
    'need-sub-detail-open-row',
    isSelected ? 'need-sub-detail-open-row--selected' : '',
    canSelectSpot ? 'need-sub-detail-open-row--button' : '',
  ].filter(Boolean).join(' ')
  const label = PLAYER_GROUP_LABELS[position.player_group] || formatPositionLabel(position.player_group)
  const countLabel = spotsLeft > 0
    ? `${spotsLeft} open`
    : 'Join waitlist'

  if (canSelectSpot) {
    return (
      <button
        aria-pressed={isSelected}
        className={className}
        type="button"
        onClick={onSelect}
      >
        <span>
          <strong>{label}</strong>
        </span>
        <em>{countLabel}</em>
      </button>
    )
  }

  return (
    <div className={className}>
      <span>
        <strong>{label}</strong>
      </span>
      <em>{countLabel}</em>
    </div>
  )
}

function getPositionSpotsLeft(position) {
  return Math.max(0, Number(position.spots_needed || 0) - countHeldSpots(position))
}

function getPlayerGroupOrder(group) {
  return {
    open: 0,
    men: 1,
    women: 2,
  }[group] ?? 3
}
