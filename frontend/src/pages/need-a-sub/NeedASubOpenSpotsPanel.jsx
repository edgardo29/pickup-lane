import { UsersRound } from 'lucide-react'
import { UserIcon } from '../../components/BrowseIcons.jsx'
import {
  NeedSubFieldPlayersIcon,
  NeedSubGoalkeeperIcon,
} from '../../components/GameFactIcons.jsx'

const POSITION_SECTIONS = [
  { id: 'field_player', title: 'Field Players', Icon: NeedSubFieldPlayersIcon },
  { id: 'goalkeeper', title: 'Goalkeepers', Icon: NeedSubGoalkeeperIcon },
]

const PLAYER_GROUP_ORDER = {
  men: 0,
  women: 1,
  open: 2,
}

const PLAYER_GROUP_LABELS = {
  men: 'Men',
  women: 'Women',
  open: 'Any',
}

export function NeedASubOpenSpotsPanel({
  onSelectPosition,
  requestGroups,
  selectedGroup,
}) {
  const groupedSections = POSITION_SECTIONS.map((section) => ({
    ...section,
    groups: requestGroups
      .filter((group) => group.position.position_label === section.id)
      .sort((a, b) => (
        (PLAYER_GROUP_ORDER[a.position.player_group] ?? 99)
        - (PLAYER_GROUP_ORDER[b.position.player_group] ?? 99)
      )),
  })).filter((section) => section.groups.length > 0)

  return (
    <section className="need-sub-manage-card need-sub-subneeds-panel">
      <h2>
        <UsersRound aria-hidden="true" />
        Open spots
      </h2>
      <div className="need-sub-open-spots-sections">
        {groupedSections.map((section) => (
          <div className="need-sub-open-spots-section" key={section.id}>
            <h3>
              <section.Icon aria-hidden="true" />
              {section.title}
            </h3>
            <div className="need-sub-need-select-list">
              {section.groups.map((group) => (
                <SubNeedSelector
                  group={group}
                  isSelected={selectedGroup?.position.id === group.position.id}
                  key={group.position.id}
                  onSelect={() => onSelectPosition(group.position.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function SubNeedSelector({ group, isSelected, onSelect }) {
  const openSpots = Math.max(0, Number(group.position.spots_needed || 0) - group.confirmed.length)
  const label = PLAYER_GROUP_LABELS[group.position.player_group] || 'Any'

  return (
    <button
      className={`need-sub-need-option ${isSelected ? 'need-sub-need-option--selected' : ''}`}
      type="button"
      onClick={onSelect}
    >
      <span className="need-sub-need-option__icon" aria-hidden="true">
        <UserIcon />
      </span>
      <span className="need-sub-need-option__body">
        <strong>{label}</strong>
      </span>
      <span className="need-sub-need-option__count">
        {openSpots > 0 ? `${openSpots} open` : 'Full'}
      </span>
      <span className="need-sub-need-option__chevron" aria-hidden="true">›</span>
    </button>
  )
}
