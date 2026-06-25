import {
  AddressIcon,
  GameDateIcon,
  GameTimeIcon,
  ParkingIcon,
  PlayersIcon,
  PriceIcon,
  VenueIcon,
} from '../../../../components/GameFactIcons.jsx'
import {
  formatGamePlayerGroup,
  formatSkillLevel,
} from '../../../create-game/createGameFormatters.js'
import {
  buildAdminOfficialGeneratedTitle,
  formatAdminOfficialMoney,
  getAdminOfficialReview,
} from './adminCreateOfficialGameFormatters.js'

function AdminCreateOfficialGamePreview({ activeStep = 1, form }) {
  const review = getAdminOfficialReview(form)
  const previewTitle = buildAdminOfficialGeneratedTitle(form)

  return (
    <aside className="admin-create-preview" aria-label="Official game preview">
      <div className="admin-create-preview__header">
        <span>Live preview</span>
        <strong title={previewTitle}>{previewTitle}</strong>
      </div>

      <PreviewSection title="Game">
        <PreviewFact icon={<GameDateIcon />} label={review.date} />
        <PreviewFact icon={<GameTimeIcon />} label={review.time} />
        <PreviewFact label={form.formatLabel || '-'} variant="dot" />
        <PreviewFact
          label={form.gamePlayerGroup ? formatGamePlayerGroup(form.gamePlayerGroup) : '-'}
          variant="dot"
        />
        <PreviewFact
          label={form.skillLevel ? formatSkillLevel(form.skillLevel) : '-'}
          variant="dot"
        />
        <PreviewFact label={capitalize(form.environmentType) || '-'} variant="dot" />
        <PreviewFact label={form.totalSpots ? `${form.totalSpots} spots` : '-'} variant="dot" />
      </PreviewSection>

      <PreviewSection title="Location">
        <PreviewFact icon={<VenueIcon />} label={form.venueName || '-'} multiline />
        <PreviewFact icon={<AddressIcon />} label={review.address || '-'} multiline />
      </PreviewSection>

      <PreviewSection title="Game settings">
        <PreviewNote
          icon={<PriceIcon />}
          label="Player price"
          text={formatAdminOfficialMoney(form.price)}
        />
        <PreviewNote
          icon={<PlayersIcon />}
          label="Booking controls"
          text={buildControlsText(form)}
        />
        <PreviewNote
          icon={<ParkingIcon />}
          label="Parking note"
          text={formatOptionalPreviewText(
            form.parkingNotes,
            'No parking note added.',
            2,
            activeStep,
          )}
        />
      </PreviewSection>
    </aside>
  )
}

function PreviewFact({ icon = null, label, multiline = false, variant = '' }) {
  const className = [
    'admin-create-preview__fact',
    multiline ? 'admin-create-preview__fact--multiline' : '',
    variant ? `admin-create-preview__fact--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <span className={className}>
      {icon}
      <span className="admin-create-preview__fact-label">{label}</span>
    </span>
  )
}

function PreviewNote({ icon, label, text }) {
  return (
    <div className="admin-create-preview__note">
      {icon}
      <div>
        <strong>{label}</strong>
        <p>{text}</p>
      </div>
    </div>
  )
}

function PreviewSection({ children, title }) {
  return (
    <section className="admin-create-preview__section">
      <span className="admin-create-preview__section-title">{title}</span>
      {children}
    </section>
  )
}

function buildControlsText(form) {
  return [
    form.allowGuests ? `Guests up to ${form.maxGuestsPerBooking}` : 'No guests',
    form.waitlistEnabled ? 'Waitlist' : 'No waitlist',
    form.isChatEnabled ? 'Chat' : 'No chat',
  ].join(' · ')
}

function formatOptionalPreviewText(value, fallbackText, stepNumber, activeStep) {
  const text = String(value || '').trim()

  if (text) {
    return text
  }

  return activeStep > stepNumber ? fallbackText : '-'
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

export default AdminCreateOfficialGamePreview
