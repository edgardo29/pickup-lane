import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'
import { formatMoney } from './browseGameFormatters.js'

export function GameCheckoutSummaryCard({
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

      <button
        className="checkout-confirm-button checkout-confirm-button--desktop"
        type="button"
        disabled={confirmDisabled}
        onClick={onConfirmBooking}
      >
        {confirmLabel}
      </button>

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
