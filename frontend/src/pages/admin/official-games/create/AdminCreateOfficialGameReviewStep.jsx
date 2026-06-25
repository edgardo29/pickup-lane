import {
  AddressIcon,
  GameDateIcon,
  GameStatusIcon,
  GameTraitIcon,
  PriceIcon,
} from '../../../../components/GameFactIcons.jsx'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import {
  formatGamePlayerGroup,
  formatSkillLevel,
} from '../../../create-game/createGameFormatters.js'
import { AdminCreateStepHeading } from './AdminCreateOfficialGameControls.jsx'
import { getAdminOfficialReview } from './adminCreateOfficialGameFormatters.js'

function AdminCreateOfficialGameReviewStep({ form, photos = [], publishError }) {
  const review = getAdminOfficialReview(form)

  return (
    <>
      <AdminCreateStepHeading
        title="Review your game"
        text="Confirm the details before publishing this listing."
      />

      <div className="admin-create-review-card">
        <ReviewSection icon={<GameTraitIcon />} title="Game Setup" variant="setup">
          <div className="admin-create-review-setup">
            <ReviewFact label="Player group" value={formatGamePlayerGroup(form.gamePlayerGroup)} />
            <ReviewFact label="Format" value={form.formatLabel} />
            <ReviewFact label="Skill level" value={formatSkillLevel(form.skillLevel)} />
            <ReviewFact label="Environment" value={capitalize(form.environmentType)} />
            <ReviewFact label="Total spots" value={`${form.totalSpots} players`} />
          </div>
        </ReviewSection>

        <ReviewSection icon={<GameDateIcon />} title="When" variant="when">
          <ReviewItem label="Date" value={review.date} />
          <ReviewItem label="Time" value={review.time} />
        </ReviewSection>

        <ReviewSection icon={<AddressIcon />} title="Where" variant="where">
          <ReviewItem label="Venue" value={form.venueName || 'Not added'} />
          <ReviewItem label="Address" value={review.address || 'Not added'} />
          <ReviewItem label="Neighborhood" value={form.neighborhood || 'Not added'} />
          <ReviewItem
            label="Parking note"
            value={form.parkingNotes || 'No parking note added.'}
            valueVariant="body"
          />
        </ReviewSection>

        <ReviewSection icon={<PriceIcon />} title="Payment" variant="payment">
          <ReviewItem label="Player price" value={review.price} valueVariant="price" />
        </ReviewSection>

        <ReviewSection icon={<GameStatusIcon />} title="Booking Controls" variant="controls">
          <ReviewItem label="Guests" value={buildGuestText(form)} />
          <ReviewItem label="Waitlist" value={form.waitlistEnabled ? 'Enabled' : 'Disabled'} />
          <ReviewItem label="Game chat" value={form.isChatEnabled ? 'Enabled' : 'Disabled'} />
          <ReviewItem
            label="Photos"
            value={photos.length ? `${photos.length} selected` : 'None selected'}
          />
        </ReviewSection>
      </div>

      <div className="admin-create-publish-card">
        <div>
          <span>Publish state</span>
          <small>The game will be published without an assigned host or initial roster.</small>
        </div>
        <strong>Official</strong>
      </div>

      <FormErrorMessage>{publishError}</FormErrorMessage>
    </>
  )
}

function ReviewSection({ children, icon, title, variant = '' }) {
  const className = [
    'admin-create-review-section',
    variant ? `admin-create-review-section--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <section className={className}>
      <header className="admin-create-review-section__heading">
        <span aria-hidden="true">{icon}</span>
        <h3>{title}</h3>
      </header>
      <div className="admin-create-review-section__rows">
        {children}
      </div>
    </section>
  )
}

function ReviewFact({ label, value }) {
  return (
    <div className="admin-create-review-fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function ReviewItem({ label, value, valueVariant = '' }) {
  const className = [
    'admin-create-review-item',
    valueVariant ? `admin-create-review-item--${valueVariant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function buildGuestText(form) {
  if (!form.allowGuests) {
    return 'Disabled'
  }

  if (Number(form.maxGuestsPerBooking) === 0) {
    return 'No guests'
  }

  return `${form.maxGuestsPerBooking} guests max`
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

export default AdminCreateOfficialGameReviewStep
