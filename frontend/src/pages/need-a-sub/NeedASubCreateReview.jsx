import {
  AddressIcon,
  GameDateIcon,
  GameNotesIcon,
  GameTraitIcon,
  PriceIcon,
  SinglePlayerIcon,
} from '../../components/GameFactIcons.jsx'
import {
  formatSkillLabel,
  formatStatus,
} from './needASubFormatters.js'

export function NeedASubCreateReview({ form, totalSpotsNeeded }) {
  return (
    <div className="need-sub-create-review">
      <ReviewSection icon={<GameTraitIcon />} title="Game Setup" variant="setup">
        <div className="need-sub-create-review-setup">
          <ReviewFact label="Player group" value={formatStatus(form.gamePlayerGroup) || 'Not selected'} />
          <ReviewFact label="Format" value={form.formatLabel || 'Not selected'} />
          <ReviewFact label="Skill level" value={formatSkillLabel(form.skillLevel)} />
          <ReviewFact label="Environment" value={form.environment ? formatStatus(form.environment) : 'Not selected'} />
        </div>
      </ReviewSection>

      <ReviewSection icon={<GameDateIcon />} title="When" variant="when">
        <ReviewItem label="Date" value={formatFormDate(form.date)} />
        <ReviewItem label="Time" value={formatFormTimeRange(form)} />
      </ReviewSection>

      <ReviewSection icon={<AddressIcon />} title="Where" variant="where">
        <ReviewItem label="Venue" value={form.locationName || 'Not set'} />
        <ReviewItem label="Address" value={formatAddress(form)} />
        {form.neighborhood && (
          <ReviewItem label="Neighborhood" value={form.neighborhood} />
        )}
      </ReviewSection>

      <ReviewSection icon={<SinglePlayerIcon />} title="Subs" variant="subs">
        <ReviewSubNeeds positions={form.positions || []} totalSpotsNeeded={totalSpotsNeeded} />
      </ReviewSection>

      <ReviewSection icon={<PriceIcon />} title="Payment" variant="payment">
        <ReviewItem label="Price due at venue" value={formatFormPrice(form.priceDue)} valueVariant="price" />
      </ReviewSection>

      <ReviewSection icon={<GameNotesIcon />} title="Notes" variant="notes">
        <ReviewItem label="Notes" value={form.notes?.trim() || 'No notes added.'} valueVariant="body" />
      </ReviewSection>
    </div>
  )
}

function ReviewSection({ children, icon, title, variant = '' }) {
  const className = [
    'need-sub-create-review-section',
    variant ? `need-sub-create-review-section--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <section className={className}>
      <header className="need-sub-create-review-section__heading">
        <span aria-hidden="true">{icon}</span>
        <h3>{title}</h3>
      </header>
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
        <span>Total needed</span>
        <strong>{totalSpotsNeeded} {totalSpotsNeeded === 1 ? 'sub' : 'subs'}</strong>
      </p>
      <div className={`need-sub-create-review-subs__groups${groups.length === 1 ? ' need-sub-create-review-subs__groups--single' : ''}`}>
        {groups.map((group) => (
          <div className="need-sub-create-review-subs__group" key={group.id}>
            <h4>{group.label}</h4>
            {group.positions.map((position, index) => (
              <div className="need-sub-create-review-subs__row" key={`${position.sort_order}-${index}`}>
                <span>{formatNeed(position)}</span>
                <strong>{formatSubCount(position.spots_needed)}</strong>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function ReviewFact({ label, value }) {
  return (
    <div className="need-sub-create-review-fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function ReviewItem({ label, value, valueVariant = '', variant = '' }) {
  const className = [
    'need-sub-create-review-item',
    variant ? `need-sub-create-review-item--${variant}` : '',
    valueVariant ? `need-sub-create-review-item--${valueVariant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function formatNeed(position) {
  if (!position.player_group) {
    return '-'
  }

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
