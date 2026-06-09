import {
  AddressIcon,
  GameDateIcon,
  GameNotesIcon,
  GameTraitIcon,
  PriceIcon,
} from '../../components/GameFactIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  StepHeading,
} from './CreateGameControls.jsx'
import { COMMUNITY_PUBLISH_FEE_CENTS } from './createGameData.js'
import {
  buildAddress,
  capitalize,
  formatGamePlayerGroup,
  formatHostPaymentMethods,
  formatMoney,
  formatSkillLevel,
} from './createGameFormatters.js'

export function ReviewStep({ form, firstPublishIsFree, isEditMode, publishError, review }) {
  return (
    <>
      <StepHeading
        title={isEditMode ? 'Review your changes' : 'Review your game'}
        text={
          isEditMode
            ? 'Confirm your updates before saving this community game.'
            : 'Confirm your details before publishing your community game.'
        }
      />

      <div className="create-game-review-card">
        <ReviewSection icon={<GameTraitIcon />} title="Game Setup" variant="setup">
          <div className="create-game-review-setup">
            <ReviewFact label="Player group" value={formatGamePlayerGroup(form.gamePlayerGroup)} />
            <ReviewFact label="Format" value={form.format} />
            <ReviewFact label="Skill level" value={formatSkillLevel(form.skillLevel)} />
            <ReviewFact label="Environment" value={capitalize(form.environment)} />
            <ReviewFact label="Total spots" value={`${form.totalSpots} players`} />
          </div>
        </ReviewSection>

        <ReviewSection icon={<GameDateIcon />} title="When" variant="when">
          <ReviewItem label="Date" value={review.date} />
          <ReviewItem label="Time" value={review.time} />
        </ReviewSection>

        <ReviewSection icon={<AddressIcon />} title="Where" variant="where">
          <ReviewItem label="Venue" value={form.venueName || 'Not added'} />
          <ReviewItem label="Address" value={buildAddress(form) || 'Not added'} />
          <ReviewItem label="Neighborhood" value={form.neighborhood || 'Not added'} />
          <ReviewItem label="Parking note" value={form.parkingNote || 'No parking note added.'} valueVariant="body" />
        </ReviewSection>

        <ReviewSection icon={<PriceIcon />} title="Payment" variant="payment">
          <ReviewItem label="Player price" value={formatMoney(Number(form.price) * 100)} valueVariant="price" />
          <ReviewItem label="Host payment" value={formatHostPaymentReview(form)} valueVariant="body" />
        </ReviewSection>

        <ReviewSection icon={<GameNotesIcon />} title="Notes" variant="notes">
          <ReviewItem label="Game notes" value={form.gameNotes || 'No game notes added.'} valueVariant="body" />
          <ReviewItem label="Host rules" value={form.hostRules || 'No host rules added.'} valueVariant="body" />
        </ReviewSection>
      </div>

      {!isEditMode && (
        <>
          <div className="create-game-fee-card">
            <div className="create-game-fee-card__copy">
              <span>Publish fee</span>
              {firstPublishIsFree && (
                <small>First community game fee waived ({formatMoney(COMMUNITY_PUBLISH_FEE_CENTS)})</small>
              )}
            </div>
            <strong>{firstPublishIsFree ? 'Free' : formatMoney(COMMUNITY_PUBLISH_FEE_CENTS)}</strong>
          </div>
        </>
      )}

      <FormErrorMessage>{publishError}</FormErrorMessage>
    </>
  )
}

function ReviewSection({ children, icon, title, variant = '' }) {
  const className = [
    'create-game-review-section',
    variant ? `create-game-review-section--${variant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <section className={className}>
      <header className="create-game-review-section__heading">
        <span aria-hidden="true">{icon}</span>
        <h3>{title}</h3>
      </header>
      <div className="create-game-review-section__rows">
        {children}
      </div>
    </section>
  )
}

function ReviewFact({ label, value }) {
  return (
    <div className="create-game-review-fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function ReviewItem({ label, value, valueVariant = '', variant = '' }) {
  const className = [
    'create-game-review-item',
    variant ? `create-game-review-item--${variant}` : '',
    valueVariant ? `create-game-review-item--${valueVariant}` : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function formatHostPaymentReview(form) {
  const hostPayment = formatHostPaymentMethods(form.paymentMethods)

  if (hostPayment !== 'Not added') {
    return hostPayment
  }

  if (Number(form.price) === 0) {
    return 'No player payment needed.'
  }

  return hostPayment
}
