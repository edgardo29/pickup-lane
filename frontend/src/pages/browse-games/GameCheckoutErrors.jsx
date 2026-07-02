import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'

export function GameCheckoutErrors({
  existingParticipant,
  isAddGuestsBlockedByParticipant,
  isAddGuestsCheckout,
  isExistingParticipantBlocked,
  isJoinWindowClosed,
  submitError,
}) {
  return (
    <>
      {isAddGuestsBlockedByParticipant && (
        <FormErrorMessage className="checkout-error">
          Only confirmed players can add guests to an existing booking.
        </FormErrorMessage>
      )}
      {isJoinWindowClosed && (
        <FormErrorMessage className="checkout-error">
          {isAddGuestsCheckout
            ? 'Attendance changes are closed for this game.'
            : 'Joining is closed for this game.'}
        </FormErrorMessage>
      )}
      {existingParticipant && !isAddGuestsCheckout && isExistingParticipantBlocked && (
        <FormErrorMessage className="checkout-error">
          {existingParticipant.participant_status === 'waitlisted'
            ? 'You are already on the waitlist for this game.'
            : 'You already joined this game.'}
        </FormErrorMessage>
      )}
      <FormErrorMessage className="checkout-error">{submitError}</FormErrorMessage>
    </>
  )
}
