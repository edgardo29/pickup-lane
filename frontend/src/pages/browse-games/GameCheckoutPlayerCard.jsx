import { Minus, Plus } from 'lucide-react'
import { UsersIcon } from '../../components/BrowseIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { getUserDisplayName } from './gameUserSelectors.js'

export function GameCheckoutPlayerCard({
  appUser,
  effectiveGuestCount,
  isAddGuestsCheckout,
  isBlockedByCapacity,
  isGuestSelectionLocked,
  isWaitlistCheckout,
  maxGuests,
  maxSelectableGuests,
  minGuestCount,
  onGuestCountChange,
  projectedGuestCount,
}) {
  return (
    <section className="checkout-card">
      <div className="checkout-section-heading">
        <h2>{isAddGuestsCheckout ? 'Guests' : isWaitlistCheckout ? 'Waitlist' : 'Players'}</h2>
        {maxGuests > 0 && (
          <span className="checkout-guest-limit">
            <UsersIcon />
            Guest limit: {projectedGuestCount}/{maxGuests}
          </span>
        )}
      </div>
      <div className="checkout-player-row">
        <span className="checkout-avatar">{getInitials(appUser)}</span>
        <div>
          <strong>{isAddGuestsCheckout ? 'Your Booking' : 'You'}</strong>
          <p>{getUserDisplayName(appUser) || 'You'}</p>
          {effectiveGuestCount > 0 && (
            <p className="checkout-party-note">
              {isAddGuestsCheckout ? 'Adding ' : '+'}
              {effectiveGuestCount} {effectiveGuestCount === 1 ? 'guest' : 'guests'}
            </p>
          )}
        </div>
      </div>
      {maxSelectableGuests > 0 && (
        <div className="checkout-guest-row">
          <div>
            <strong>{isAddGuestsCheckout ? 'Guests to add' : 'Guests'}</strong>
          </div>
          <div className="checkout-guest-stepper" aria-label="Guest count">
            <button
              type="button"
              disabled={isGuestSelectionLocked || effectiveGuestCount <= minGuestCount}
              onClick={() => onGuestCountChange((count) => Math.max(count - 1, minGuestCount))}
            >
              <Minus aria-hidden="true" />
            </button>
            <span>{effectiveGuestCount}</span>
            <button
              type="button"
              disabled={isGuestSelectionLocked || effectiveGuestCount >= maxSelectableGuests}
              onClick={() => onGuestCountChange((count) => Math.min(count + 1, maxSelectableGuests))}
            >
              <Plus aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
      {isBlockedByCapacity && (
        <FormErrorMessage className="checkout-error">
          {isAddGuestsCheckout
            ? 'No guest spots are available right now.'
            : 'Not enough spots are available for this join.'}
        </FormErrorMessage>
      )}
    </section>
  )
}

function getInitials(user) {
  const first = user?.first_name?.[0] || ''
  const last = user?.last_name?.[0] || ''
  return `${first}${last}`.toUpperCase() || 'PL'
}
