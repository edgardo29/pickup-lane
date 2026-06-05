import {
  AddressIcon,
  GameDateIcon,
  GameNotesIcon,
  GameTimeIcon,
  NeedSubFieldPlayersIcon,
  NeedSubGoalkeeperIcon,
  PriceIcon,
} from '../../components/GameFactIcons.jsx'
import {
  formatSkillLabel,
  formatStatus,
} from './needASubFormatters.js'

export function NeedASubCreatePreview({ form, totalSpotsNeeded }) {
  const subCount = Number(totalSpotsNeeded || 0)
  const displaySubCount = subCount || 1

  return (
    <aside className="need-sub-create-preview" aria-label="Sub post preview">
      <div className="need-sub-create-preview__header">
        <span className="need-sub-create-preview__eyebrow">Live preview</span>
        <strong>Need <span className="need-sub-create-preview__count">{displaySubCount}</span> {displaySubCount === 1 ? 'Sub' : 'Subs'}</strong>
      </div>

      <PreviewSection title="Game">
        <PreviewFact icon={<GameDateIcon />} label={formatPreviewDate(form.date)} />
        <PreviewFact icon={<GameTimeIcon />} label={formatPreviewTimeRange(form)} />
        <PreviewFact label={form.formatLabel || '-'} variant="dot" />
        <PreviewFact label={formatStatus(form.gamePlayerGroup) || '-'} variant="dot" />
        <PreviewFact label={formatSkillLabel(form.skillLevel) || '-'} variant="dot" />
        <PreviewFact label={form.environment ? formatStatus(form.environment) : '-'} variant="dot" />
      </PreviewSection>

      <PreviewSection title="Subs">
        <PreviewSubNeeds positions={form.positions || []} />
      </PreviewSection>

      <PreviewSection title="Location">
        <PreviewFact icon={<AddressIcon />} label={buildPreviewLocation(form)} multiline />
      </PreviewSection>

      <PreviewSection title="Notes & Payment">
        <PreviewNote
          icon={<PriceIcon />}
          label="Price due at venue"
          text={formatPreviewPrice(form.priceDue)}
        />
        <PreviewNote
          icon={<GameNotesIcon />}
          label="Notes"
          text={form.notes?.trim() || 'Add optional notes for subs.'}
        />
      </PreviewSection>
    </aside>
  )
}

function PreviewSubNeeds({ positions }) {
  const fieldPlayers = positions.filter((position) => position.position_label === 'field_player')
  const goalkeepers = positions.filter((position) => position.position_label === 'goalkeeper')
  const groups = [
    { id: 'field', icon: NeedSubFieldPlayersIcon, label: 'Field Players', positions: fieldPlayers },
    { id: 'goalkeeper', icon: NeedSubGoalkeeperIcon, label: 'Goalkeepers', positions: goalkeepers },
  ].filter((group) => group.positions.length > 0)

  return (
    <div className="need-sub-create-preview__subs">
      <div className={`need-sub-create-preview__subs-groups${groups.length === 1 ? ' need-sub-create-preview__subs-groups--single' : ''}`}>
        {groups.map((group) => {
          const GroupIcon = group.icon

          return (
            <div className="need-sub-create-preview__subs-group" key={group.id}>
              <h4>
                <GroupIcon />
                <span>{group.label}</span>
              </h4>
              {group.positions.map((position, index) => (
                <div className="need-sub-create-preview__need" key={`${position.sort_order}-${index}`}>
                  <span>{formatNeed(position)}</span>
                <strong>{formatSubCount(position.spots_needed)}</strong>
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PreviewSection({ children, title }) {
  return (
    <section className="need-sub-create-preview__section">
      <span className="need-sub-create-preview__section-title">{title}</span>
      {children}
    </section>
  )
}

function PreviewFact({ icon = null, label, multiline = false, variant = '' }) {
  const className = [
    'need-sub-create-preview__fact',
    multiline ? 'need-sub-create-preview__fact--multiline' : '',
    variant ? `need-sub-create-preview__fact--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <span className={className}>
      {icon}
      <span>{label}</span>
    </span>
  )
}

function PreviewNote({ icon, label, text }) {
  return (
    <div className="need-sub-create-preview__note">
      {icon}
      <div>
        <strong>{label}</strong>
        <p>{text}</p>
      </div>
    </div>
  )
}

function buildPreviewLocation(form) {
  const locationName = form.locationName?.trim()
  const addressLine = form.addressLine1?.trim()
  const city = form.city?.trim()
  const state = form.state?.trim()
  const postalCode = form.postalCode?.trim()
  const stateLine = [state, postalCode].filter(Boolean).join(' ')
  const cityLine = [city, stateLine].filter(Boolean).join(', ')
  const address = [addressLine, cityLine].filter(Boolean).join(' · ')
  const venueLine = [locationName, [city, state].filter(Boolean).join(', ')]
    .filter(Boolean)
    .join(' · ')

  return address || venueLine || '-'
}

function formatNeed(position) {
  if (!position.player_group) {
    return 'Select player type'
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

function formatPreviewDate(value) {
  if (!value) {
    return 'Choose date'
  }

  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`))
}

function formatPreviewTimeRange(form) {
  return `${formatPreviewTime(form.startTime)} - ${formatPreviewTime(form.endTime)}`
}

function formatPreviewTime(value) {
  if (!value) {
    return 'Time'
  }

  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(`2026-01-01T${value}:00`))
}

function formatPreviewPrice(value) {
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
