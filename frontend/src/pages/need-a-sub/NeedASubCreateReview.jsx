import {
  AddressIcon,
  GameDateIcon,
  GameFormatIcon,
  GameIndoorIcon,
  GameNotesIcon,
  GameOutdoorIcon,
  GameSkillIcon,
  GameTimeIcon,
  NeighborhoodIcon,
  PriceIcon,
  SinglePlayerIcon,
  VenueIcon,
} from '../../components/GameFactIcons.jsx'
import {
  formatSkillLabel,
  formatStatus,
} from './needASubFormatters.js'

export function NeedASubCreateReview({ form, totalSpotsNeeded }) {
  return (
    <div className="need-sub-create-review">
      <ReviewSection title="Game" variant="game">
        <ReviewItem icon={<GameDateIcon />} label="Date" value={formatFormDate(form.date)} />
        <ReviewItem icon={<GameTimeIcon />} label="Time" value={formatFormTimeRange(form)} />
        <ReviewItem icon={<GameFormatIcon />} label="Format" value={`${form.formatLabel} · ${formatStatus(form.gamePlayerGroup)}`} />
        <ReviewItem icon={getEnvironmentIcon(form.environment)} label="Environment" value={form.environment ? formatStatus(form.environment) : 'Not selected'} />
        <ReviewItem icon={<GameSkillIcon />} label="Skill level" value={formatSkillLabel(form.skillLevel)} />
      </ReviewSection>

      <ReviewSection title="Subs" variant="subs">
        <ReviewSubNeeds positions={form.positions || []} totalSpotsNeeded={totalSpotsNeeded} />
      </ReviewSection>

      <ReviewSection title="Location" variant="location">
        <ReviewItem icon={<VenueIcon />} label="Venue" value={form.locationName || 'Not set'} wide />
        <ReviewItem icon={<AddressIcon />} label="Address" value={formatAddress(form)} wide />
        {form.neighborhood && (
          <ReviewItem icon={<NeighborhoodIcon />} label="Neighborhood" value={form.neighborhood} wide />
        )}
      </ReviewSection>

      <ReviewSection title="Notes & Payment" variant="notes">
        <ReviewItem icon={<PriceIcon />} label="Price due at venue" value={formatFormPrice(form.priceDue)} />
        <ReviewItem icon={<GameNotesIcon />} label="Notes" value={form.notes?.trim() || 'No notes added.'} variant="notes" wide />
      </ReviewSection>
    </div>
  )
}

function getEnvironmentIcon(environment) {
  return environment === 'outdoor' ? <GameOutdoorIcon /> : <GameIndoorIcon />
}

function ReviewSection({ children, title, variant = '', wide = false }) {
  const className = [
    'need-sub-create-review-section',
    wide ? 'need-sub-create-review-section--wide' : '',
    variant ? `need-sub-create-review-section--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <section className={className}>
      <h3>{title}</h3>
      <div className="need-sub-create-review-section__rows">
        {children}
      </div>
    </section>
  )
}

function ReviewSubNeeds({ positions, totalSpotsNeeded }) {
  const fieldPlayers = positions.filter((position) => position.position_label === 'field_player')
  const goalkeepers = positions.filter((position) => position.position_label === 'goalkeeper')
  const groups = [
    { id: 'field', label: 'Field Players', positions: fieldPlayers },
    { id: 'goalkeeper', label: 'Goalkeepers', positions: goalkeepers },
  ].filter((group) => group.positions.length > 0)

  return (
    <div className="need-sub-create-review-subs">
      <p className="need-sub-create-review-subs__total">
        Total needed: <strong>{totalSpotsNeeded} {totalSpotsNeeded === 1 ? 'sub' : 'subs'}</strong>
      </p>
      <div className={`need-sub-create-review-subs__groups${groups.length === 1 ? ' need-sub-create-review-subs__groups--single' : ''}`}>
        {groups.map((group) => (
          <div className="need-sub-create-review-subs__group" key={group.id}>
            <h4>{group.label}</h4>
            {group.positions.map((position, index) => (
              <div className="need-sub-create-review-subs__row" key={`${position.sort_order}-${index}`}>
                <SinglePlayerIcon />
                <span>{formatNeed(position)}</span>
                <span className="need-sub-create-review-subs__dot" aria-hidden="true">·</span>
                <strong>{formatSubCount(position.spots_needed)}</strong>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function ReviewItem({ icon, label, value, variant = '', wide = false }) {
  const className = [
    'need-sub-create-review-item',
    wide ? 'need-sub-create-review-item--wide' : '',
    variant ? `need-sub-create-review-item--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={className}>
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function formatNeed(position) {
  if (position.player_group === 'open') {
    return 'Any'
  }

  if (position.player_group === 'men') {
    return 'Men'
  }

  if (position.player_group === 'women') {
    return 'Women'
  }

  return formatStatus(position.player_group)
}

function formatSubCount(value) {
  const count = Number(value || 0)
  return `${count} ${count === 1 ? 'sub' : 'subs'}`
}

function formatAddress(form) {
  const cityLine = [form.city, form.state, form.postalCode].filter(Boolean).join(', ')
  return [form.addressLine1, cityLine].filter(Boolean).join(' · ') || 'Not set'
}

function formatFormDate(value) {
  if (!value) {
    return 'Not set'
  }

  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`))
}

function formatFormTimeRange(form) {
  return `${formatFormTime(form.startTime)} - ${formatFormTime(form.endTime)}`
}

function formatFormTime(value) {
  if (!value) {
    return 'Not set'
  }

  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(`2026-01-01T${value}:00`))
}

function formatFormPrice(value) {
  const amount = Number(String(value || '').trim() || 0)

  if (!Number.isFinite(amount) || amount <= 0) {
    return 'Free'
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(amount)
}
