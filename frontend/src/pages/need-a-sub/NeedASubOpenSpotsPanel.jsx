import { UserIcon } from '../../components/BrowseIcons.jsx'
import { formatNeedLabel } from './needASubFormatters.js'

export function NeedASubOpenSpotsPanel({
  onSelectPosition,
  requestGroups,
  selectedGroup,
}) {
  return (
    <section className="need-sub-manage-card need-sub-subneeds-panel">
      <h2>Open spots</h2>
      <div className="need-sub-need-select-list">
        {requestGroups.map((group) => (
          <SubNeedSelector
            group={group}
            isSelected={selectedGroup?.position.id === group.position.id}
            key={group.position.id}
            onSelect={() => onSelectPosition(group.position.id)}
          />
        ))}
      </div>
    </section>
  )
}

function SubNeedSelector({ group, isSelected, onSelect }) {
  const openSpots = Math.max(0, Number(group.position.spots_needed || 0) - group.confirmed.length)
  const label = formatNeedLabel(group.position).replace(/^\d+\s+Subs?\s+·\s+/, '')

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
        <small>{openSpots > 0 ? `${openSpots} open` : 'Full'}</small>
      </span>
    </button>
  )
}
