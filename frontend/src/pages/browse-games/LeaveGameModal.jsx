import { useState } from 'react'
import { UsersIcon } from '../../components/BrowseIcons.jsx'

export function LeaveGameModal({
  addableGuestCount = 0,
  canAddGuests = false,
  guestCount,
  guestMax = 0,
  isLeaving,
  isUpdatingGuests,
  isWaitlisted,
  onAddGuests,
  onClose,
  onConfirm,
  onRemoveGuests,
}) {
  const [nextGuestCount, setNextGuestCount] = useState(guestCount)
  const title = isWaitlisted ? 'Edit waitlist?' : 'Edit attendance?'
  const maxSelectableGuests = Math.min(guestMax, guestCount + addableGuestCount)
  const canDecreaseGuests = nextGuestCount > 0
  const canIncreaseGuests = nextGuestCount < maxSelectableGuests
  const guestDelta = nextGuestCount - guestCount
  const hasGuestChanges = guestDelta !== 0
  const guestActionLabel = guestDelta > 0
    ? 'Continue to Checkout'
    : guestDelta < 0
      ? isUpdatingGuests
        ? 'Updating...'
        : 'Update Guests'
      : 'No Changes'

  function changeGuestCount(delta) {
    setNextGuestCount((currentCount) => (
      Math.min(Math.max(currentCount + delta, 0), maxSelectableGuests)
    ))
  }

  function handleGuestUpdate() {
    if (!hasGuestChanges) {
      return
    }

    if (guestDelta > 0) {
      onAddGuests(guestDelta)
      return
    }

    onRemoveGuests(Math.abs(guestDelta))
  }

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="details-confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="details-leave-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="details-leave-title" className="details-confirm-modal__title">
          <span className="details-confirm-modal__title-icon">
            <UsersIcon />
          </span>
          {title}
        </h2>
        {isWaitlisted && <p>You will give up your waitlist position.</p>}
        {!isWaitlisted && (
          <div className="details-attendance-actions">
            {guestMax > 0 && (
              <div className="details-attendance-actions__group details-attendance-actions__group--guests">
                <div>
                  <strong>Guests</strong>
                  <span>{nextGuestCount}/{guestMax} on your booking</span>
                </div>
                <div className="details-attendance-stepper" aria-label="Guest count">
                  <button
                    type="button"
                    aria-label="Decrease guests"
                    disabled={!canDecreaseGuests || isLeaving || isUpdatingGuests}
                    onClick={() => changeGuestCount(-1)}
                  >
                    −
                  </button>
                  <span>{nextGuestCount}</span>
                  <button
                    type="button"
                    aria-label="Increase guests"
                    disabled={!canIncreaseGuests || isLeaving || isUpdatingGuests || (!canAddGuests && nextGuestCount >= guestCount)}
                    onClick={() => changeGuestCount(1)}
                  >
                    +
                  </button>
                </div>
                <button
                  type="button"
                  disabled={!hasGuestChanges || isLeaving || isUpdatingGuests}
                  onClick={handleGuestUpdate}
                >
                  {guestActionLabel}
                </button>
              </div>
            )}

            {guestMax <= 0 && guestCount > 0 && (
              <div className="details-attendance-actions__group">
                <strong>Guests</strong>
                <span>{guestCount} on your booking</span>
                <div className="details-attendance-actions__inline">
                  <button
                    type="button"
                    disabled={isLeaving || isUpdatingGuests}
                    onClick={() => onRemoveGuests(1)}
                  >
                    {isUpdatingGuests ? 'Updating...' : 'Remove 1 Guest'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        <div className="details-confirm-modal__actions">
          <button type="button" onClick={onClose}>
            Keep Spot
          </button>
          <button className="danger" type="button" disabled={isLeaving} onClick={onConfirm}>
            {isLeaving ? 'Leaving...' : isWaitlisted ? 'Leave Waitlist' : 'Leave Game'}
          </button>
        </div>
      </section>
    </div>
  )
}
