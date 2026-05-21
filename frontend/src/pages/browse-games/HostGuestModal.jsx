import { useState } from 'react'
import { UsersIcon } from '../../components/BrowseIcons.jsx'

export function HostGuestModal({
  addableCount,
  guestCount,
  guestMax,
  isAdding,
  isRemoving,
  onClose,
  onSave,
}) {
  const [nextGuestCount, setNextGuestCount] = useState(guestCount)
  const isSaving = isAdding || isRemoving
  const maxSelectableGuests = Math.min(guestMax, guestCount + addableCount)
  const canDecrease = nextGuestCount > 0
  const canIncrease = nextGuestCount < maxSelectableGuests
  const hasChanges = nextGuestCount !== guestCount

  function changeGuestCount(delta) {
    setNextGuestCount((currentCount) => (
      Math.min(Math.max(currentCount + delta, 0), maxSelectableGuests)
    ))
  }

  function handleSubmit(event) {
    event.preventDefault()

    if (!hasChanges) {
      onClose()
      return
    }

    onSave(nextGuestCount)
  }

  return (
    <div className="details-modal-backdrop" role="presentation" onClick={onClose}>
      <form
        className="details-confirm-modal details-host-guest-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="host-guest-modal-title"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 id="host-guest-modal-title" className="details-confirm-modal__title">
          <span className="details-confirm-modal__title-icon">
            <UsersIcon />
          </span>
          Manage Guests
        </h2>

        <div className="details-attendance-actions details-host-guest-modal__body">
          <div className="details-attendance-actions__group details-attendance-actions__group--guests">
            <div>
              <strong>Guests</strong>
              <span>{nextGuestCount}/{guestMax} reserved for your game</span>
            </div>
            <div className="details-attendance-stepper" aria-label="Host guest count">
              <button
                type="button"
                aria-label="Remove one guest"
                disabled={!canDecrease || isSaving}
                onClick={() => changeGuestCount(-1)}
              >
                −
              </button>
              <span>{nextGuestCount}</span>
              <button
                type="button"
                aria-label="Add one guest"
                disabled={!canIncrease || isSaving}
                onClick={() => changeGuestCount(1)}
              >
                +
              </button>
            </div>
            <button type="submit" disabled={!hasChanges || isSaving}>
              {isSaving ? 'Saving...' : hasChanges ? 'Save Changes' : 'No Changes'}
            </button>
          </div>
        </div>

        {maxSelectableGuests < guestMax && (
          <p className="details-host-guest-modal__limit">
            Only {maxSelectableGuests} can be reserved right now.
          </p>
        )}

        <div className="details-confirm-modal__actions">
          <button
            type="button"
            disabled={isSaving}
            onClick={onClose}
          >
            Cancel
          </button>
          <button className="primary" type="submit" disabled={isSaving}>
            {isSaving ? 'Saving...' : hasChanges ? 'Save Changes' : 'Done'}
          </button>
        </div>
      </form>
    </div>
  )
}
