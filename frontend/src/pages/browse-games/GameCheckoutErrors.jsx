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
        <p className="checkout-error">
          Only confirmed players can add guests to an existing booking.
        </p>
      )}
      {isJoinWindowClosed && (
        <p className="checkout-error">
          {isAddGuestsCheckout
            ? 'Attendance changes are closed for this game.'
            : 'Joining is closed for this game.'}
        </p>
      )}
      {existingParticipant && !isAddGuestsCheckout && isExistingParticipantBlocked && (
        <p className="checkout-error">
          {existingParticipant.participant_status === 'waitlisted'
            ? 'You are already on the waitlist for this game.'
            : 'You already joined this game.'}
        </p>
      )}
      {submitError && <p className="checkout-error">{submitError}</p>}
    </>
  )
}
