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
  quote,
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
      {quote?.credit_applied_cents > 0 && (
        <CheckoutLine
          label="Game credit applied"
          value={`-${formatMoney(quote.credit_applied_cents)}`}
        />
      )}
      {quote?.minimum_charge_adjustment_cents > 0 && (
        <CheckoutLine
          label="Covered by Pickup Lane"
          value={`-${formatMoney(quote.minimum_charge_adjustment_cents)}`}
        />
      )}
      {isWaitlistCheckout && <p className="checkout-summary-note">No charge now</p>}
      <div className="checkout-total">
        <span>{isWaitlistCheckout ? 'Estimated later charge' : quote ? 'Amount due' : 'Total'}</span>
        <strong>{formatMoney(quote ? quote.final_amount_due_cents : total)}</strong>
      </div>
      {quote?.available_credit_cents > 0 && (
        <p className="checkout-summary-note">
          Available game credit: {formatMoney(quote.available_credit_cents)}
        </p>
      )}
      {isWaitlistCheckout && quote && (
        <p className="checkout-summary-note">Credit is applied when a spot opens; your balance may change.</p>
      )}

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
