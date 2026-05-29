import {
  BuildingIcon,
  CalendarIcon,
  ChatIcon,
  ClipboardListIcon,
  ClockIcon,
  DollarIcon,
  MapPinIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  ReviewRow,
  StepHeading,
} from './CreateGameControls.jsx'
import { COMMUNITY_PUBLISH_FEE_CENTS } from './createGameData.js'
import {
  capitalize,
  formatHostPaymentMethods,
  formatMoney,
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
        <ReviewSection title="Game details">
          <ReviewRow icon={<CalendarIcon />} label="Date" value={review.date} />
          <ReviewRow icon={<ClockIcon />} label="Time" value={review.time} />
          <ReviewRow icon={<UsersIcon />} label="Format" value={form.format} />
          <ReviewRow
            icon={<BuildingIcon />}
            label="Indoor / Outdoor"
            value={capitalize(form.environment)}
          />
          <ReviewRow icon={<UsersIcon />} label="Total spots" value={`${form.totalSpots} players`} />
          <ReviewRow icon={<DollarIcon />} label="Price per player" value={formatMoney(Number(form.price) * 100)} />
        </ReviewSection>

        <ReviewSection title="Location">
          <ReviewRow icon={<BuildingIcon />} label="Venue" value={form.venueName || 'Not added'} />
          <ReviewRow icon={<MapPinIcon />} label="Street address" value={form.street || 'Not added'} />
          <ReviewRow icon={<MapPinIcon />} label="City" value={form.city || 'Not added'} />
          <ReviewRow icon={<MapPinIcon />} label="State" value={form.state || 'Not added'} />
          <ReviewRow icon={<MapPinIcon />} label="ZIP code" value={form.zip || 'Not added'} />
          <ReviewRow icon={<MapPinIcon />} label="Neighborhood" value={form.neighborhood || 'Not added'} />
          <ReviewRow icon={<ChatIcon />} label="Parking note" value={form.parkingNote || 'No parking note added.'} wide />
        </ReviewSection>

        <ReviewSection title="Notes & payment" wide>
          <ReviewRow icon={<ChatIcon />} label="Game notes" value={form.gameNotes || 'No notes added.'} wide />
          <ReviewRow icon={<ClipboardListIcon />} label="Host rules" value={form.hostRules || 'No host rules added.'} wide />
          <ReviewRow
            icon={<DollarIcon />}
            label="Host payment"
            value={
              Number(form.price) === 0
                ? 'No payment needed'
                : formatHostPaymentMethods(form.paymentMethods)
            }
          />
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

      {publishError && <p className="create-game-error">{publishError}</p>}
    </>
  )
}

function ReviewSection({ children, title, wide = false }) {
  return (
    <section className={`create-game-review-section${wide ? ' create-game-review-section--wide' : ''}`}>
      <h3>{title}</h3>
      <div className="create-game-review-section__rows">
        {children}
      </div>
    </section>
  )
}
