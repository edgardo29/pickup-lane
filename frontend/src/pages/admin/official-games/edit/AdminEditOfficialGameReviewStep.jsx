import {
  AddressIcon,
  GameDateIcon,
  GameNotesIcon,
  GameStatusIcon,
  GameTraitIcon,
  PriceIcon,
} from '../../../../components/GameFactIcons.jsx'
import { FormErrorMessage } from '../../../../components/FormErrorMessage.jsx'
import {
  formatGamePlayerGroup,
  formatSkillLevel,
} from '../../../create-game/createGameFormatters.js'
import { AdminCreateStepHeading } from '../create/AdminCreateOfficialGameControls.jsx'
import { getAdminOfficialReview } from '../create/adminCreateOfficialGameFormatters.js'

function AdminEditOfficialGameReviewStep({ form, saveError }) {
  const review = getAdminOfficialReview(form)

  return (
    <>
      <AdminCreateStepHeading
        title="Review your changes"
        text="Confirm the official game details before saving."
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
          <ReviewItem label="Venue" value={form.venueName || 'Venue unavailable'} />
          <ReviewItem label="Address" value={review.address || 'Address unavailable'} />
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
        </ReviewSection>

        <ReviewSection icon={<GameNotesIcon />} title="Player Notes" variant="notes">
          <ReviewItem
            label="Player instructions"
            value={form.playerInstructions || 'No player instructions added.'}
            valueVariant="body"
          />
          <ReviewItem
            label="Internal reason"
            value={form.reason || 'No internal reason added.'}
            valueVariant="body"
          />
        </ReviewSection>
      </div>

      <FormErrorMessage>{saveError}</FormErrorMessage>
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

export default AdminEditOfficialGameReviewStep
