import { CircleCheck } from 'lucide-react'
import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { formatMoney } from './browseGameFormatters.js'

export function GameCheckoutSummaryCard({
  actionMessage,
  confirmDisabled,
  confirmLabel,
  effectiveGuestCount,
  isAddGuestsCheckout,
  isWaitlistCheckout,
  onConfirmBooking,
  platformFee,
  price,
  total,
}) {
  return (
    <aside className="checkout-card checkout-summary-card">
      <h2>Order summary</h2>
      {!isAddGuestsCheckout && (
        <CheckoutLine
          label="1 x Player"
          value={formatMoney(price)}
        />
      )}
      {effectiveGuestCount > 0 && (
        <CheckoutLine
          label={`${effectiveGuestCount} x ${effectiveGuestCount === 1 ? 'Guest' : 'Guests'}`}
          value={formatMoney(price * effectiveGuestCount)}
        />
      )}
      {!isWaitlistCheckout && <CheckoutLine label="Pickup Lane fee" value={formatMoney(platformFee)} />}
      {isWaitlistCheckout && <p className="checkout-summary-note">No charge now</p>}
      <div className="checkout-total">
        <span>Total</span>
        <strong>{formatMoney(total)}</strong>
      </div>

      {isWaitlistCheckout && (
        <p className="checkout-summary-waitlist-note">
          You won’t be charged now. You’ll only be charged if a spot opens and you’re moved
          into the game.
        </p>
      )}

      <div className="checkout-summary-action checkout-summary-action--desktop">
        <button
          className="checkout-confirm-button"
          type="button"
          disabled={confirmDisabled}
          onClick={onConfirmBooking}
        >
          <CircleCheck aria-hidden="true" />
          <span>{confirmLabel}</span>
        </button>

        <FormErrorMessage className="checkout-action-error">
          {actionMessage}
        </FormErrorMessage>
      </div>

      <p className="checkout-secure-note">
        <ShieldCheckIcon />
        Secure checkout
      </p>
    </aside>
  )
}

function CheckoutLine({ label, value }) {
  return (
    <div className="checkout-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
