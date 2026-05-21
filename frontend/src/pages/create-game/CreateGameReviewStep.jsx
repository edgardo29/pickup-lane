import {
  BuildingIcon,
  CalendarIcon,
  ChatIcon,
  ClockIcon,
  MapPinIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  ReviewRow,
  StepHeading,
} from './CreateGameControls.jsx'
import { COMMUNITY_PUBLISH_FEE_CENTS } from './createGameData.js'
import {
  buildAddress,
  capitalize,
  formatHostPaymentMethods,
  formatMoney,
} from './createGameFormatters.js'

export function ReviewStep({ form, firstPublishIsFree, isEditMode, publishError, review }) {
  const publishFeeCents = firstPublishIsFree ? 0 : COMMUNITY_PUBLISH_FEE_CENTS

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
        <ReviewRow icon={<CalendarIcon />} label="Date" value={review.date} />
        <ReviewRow icon={<ClockIcon />} label="Time" value={review.time} />
        <ReviewRow icon={<UsersIcon />} label="Format" value={form.format} />
        <ReviewRow
          icon={<BuildingIcon />}
          label="Indoor / Outdoor"
          value={capitalize(form.environment)}
        />
        <ReviewRow icon={<UsersIcon />} label="Total spots" value={`${form.totalSpots} players`} />
        <ReviewRow icon={<SoccerBallIcon />} label="Price per player" value={formatMoney(Number(form.price) * 100)} />
        <hr />
        <ReviewRow icon={<MapPinIcon />} label="Venue" value={form.venueName || 'Not added'} />
        <ReviewRow icon={<MapPinIcon />} label="Address" value={buildAddress(form) || 'Not added'} />
        <hr />
        <ReviewRow icon={<ChatIcon />} label="Game notes" value={form.gameNotes || 'No notes added.'} />
        <ReviewRow
          icon={<SoccerBallIcon />}
          label="Host payment"
          value={
            Number(form.price) === 0
              ? 'No payment needed'
              : formatHostPaymentMethods(form.paymentMethods)
          }
        />
      </div>

      {!isEditMode && (
        <>
          <div className="create-game-fee-card">
            <div>
              <span>Publish fee</span>
              <strong>{firstPublishIsFree ? 'Free' : formatMoney(COMMUNITY_PUBLISH_FEE_CENTS)}</strong>
            </div>
            <p>{firstPublishIsFree ? 'First community game waived.' : 'Charged once when published.'}</p>
          </div>

          <div className="create-game-total-row">
            <span>Due today</span>
            <strong>{formatMoney(publishFeeCents)}</strong>
          </div>
        </>
      )}

      {publishError && <p className="create-game-error">{publishError}</p>}
    </>
  )
}
