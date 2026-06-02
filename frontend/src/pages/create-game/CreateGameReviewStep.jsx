import {
  AddressIcon,
  GameDateIcon,
  GameFormatIcon,
  GameIndoorIcon,
  GameNotesIcon,
  GameOutdoorIcon,
  GamePlayerGroupIcon,
  GameSkillIcon,
  GameSpotsIcon,
  GameTimeIcon,
  HostPaymentIcon,
  HostRulesIcon,
  NeighborhoodIcon,
  ParkingIcon,
  PriceIcon,
  VenueIcon,
} from '../../components/GameFactIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  ReviewRow,
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
        <ReviewSection title="Game">
          <ReviewRow icon={<GameDateIcon />} label="Date" value={review.date} />
          <ReviewRow icon={<GameTimeIcon />} label="Time" value={review.time} />
          <ReviewRow icon={<GameFormatIcon />} label="Format" value={form.format} />
          <ReviewRow icon={<GamePlayerGroupIcon />} label="Player group" value={formatGamePlayerGroup(form.gamePlayerGroup)} />
          <ReviewRow icon={<GameSkillIcon />} label="Skill level" value={formatSkillLevel(form.skillLevel)} />
          <ReviewRow
            icon={getEnvironmentIcon(form.environment)}
            label="Indoor/Outdoor"
            value={capitalize(form.environment)}
          />
          <ReviewRow icon={<GameSpotsIcon />} label="Total spots" value={`${form.totalSpots} players`} />
          <ReviewRow icon={<PriceIcon />} label="Price per player" value={formatMoney(Number(form.price) * 100)} />
        </ReviewSection>

        <ReviewSection title="Location">
          <ReviewRow icon={<VenueIcon />} label="Venue" value={form.venueName || 'Not added'} />
          <ReviewRow icon={<AddressIcon />} label="Address" value={buildAddress(form) || 'Not added'} />
          <ReviewRow icon={<NeighborhoodIcon />} label="Neighborhood" value={form.neighborhood || 'Not added'} />
          <ReviewRow icon={<ParkingIcon />} label="Parking note" value={form.parkingNote || 'No parking note added.'} wide />
        </ReviewSection>

        <ReviewSection title="Notes & payment" wide>
          <ReviewRow icon={<GameNotesIcon />} label="Game notes" value={form.gameNotes || 'No notes added.'} wide />
          <ReviewRow icon={<HostRulesIcon />} label="Host rules" value={form.hostRules || 'No host rules added.'} wide />
          <ReviewRow
            icon={<HostPaymentIcon />}
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

      <FormErrorMessage>{publishError}</FormErrorMessage>
    </>
  )
}

function getEnvironmentIcon(environment) {
  return environment === 'outdoor' ? <GameOutdoorIcon /> : <GameIndoorIcon />
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
