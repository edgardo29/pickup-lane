import { CreditCard } from 'lucide-react'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  formatPaymentMethodExpiration,
  isPaymentMethodExpired,
} from '../../lib/paymentMethodCards.js'
import { formatMoney, formatPaymentMethod } from './browseGameFormatters.js'

export function GameCheckoutPaymentCard({
  autoChargeConsent = false,
  canAddPaymentMethod = true,
  isPaidWaitlistCheckout = false,
  isStripeCheckout,
  onAddPaymentMethod,
  onAutoChargeConsentChange,
  onChangePaymentMethod,
  onRetryPaymentMethods,
  paymentMethod,
  paymentMethods = [],
  paymentMethodsError = '',
  paymentRequired = true,
  setupError = '',
  stripePaymentsDisabled,
  stripeStatusMessage,
  stripeUnavailable,
  waitlistChargeCents = 0,
}) {
  if (isStripeCheckout) {
    const hasSavedCards = paymentMethods.length > 0
    const selectedCardIsExpired = isPaymentMethodExpired(paymentMethod)

    return (
      <section className="checkout-card">
        <div className="checkout-payment-heading">
          <h2>Payment</h2>
          {hasSavedCards && !stripePaymentsDisabled && (
            <button
              className="checkout-payment-change"
              onClick={onChangePaymentMethod}
              type="button"
            >
              Change
            </button>
          )}
        </div>
        {stripePaymentsDisabled && (
          <FormErrorMessage className="checkout-payment-error">
            Official game payments are disabled for this demo.
          </FormErrorMessage>
        )}
        {stripeUnavailable && (
          <FormErrorMessage className="checkout-payment-error">
            Secure payment is not configured.
          </FormErrorMessage>
        )}
        {paymentMethodsError && (
          <FormErrorMessage className="checkout-payment-error">
            {paymentMethodsError}{' '}
            <button className="checkout-payment-change" type="button" onClick={onRetryPaymentMethods}>
              Retry
            </button>
          </FormErrorMessage>
        )}
        {!stripePaymentsDisabled && !stripeUnavailable && hasSavedCards && paymentMethod && (
          <div
            className={`checkout-selected-payment${
              selectedCardIsExpired ? ' checkout-selected-payment--expired' : ''
            }`}
          >
            <strong>{formatPaymentMethod(paymentMethod)}</strong>
            <span>
              {selectedCardIsExpired ? 'Expired' : 'Selected for this booking'}
              {' · '}
              {selectedCardIsExpired ? 'Expired' : 'Expires'}{' '}
              {formatPaymentMethodExpiration(paymentMethod)}
            </span>
          </div>
        )}
        {!stripePaymentsDisabled && !stripeUnavailable && !hasSavedCards && !paymentRequired && (
          <p className="checkout-payment-note">Nothing is due, so no card is needed.</p>
        )}
        {!stripePaymentsDisabled && !stripeUnavailable && !paymentMethodsError &&
          !hasSavedCards && paymentRequired && (
          <div className="checkout-payment-empty">
            <div>
              <strong>No payment method</strong>
              <span>
                {isPaidWaitlistCheckout
                  ? 'Add a card to join this waitlist.'
                  : 'Add a card to reserve your spot.'}
              </span>
            </div>
            <button disabled={!canAddPaymentMethod} type="button" onClick={onAddPaymentMethod}>
              <CreditCard aria-hidden="true" />
              <span>Add card</span>
            </button>
          </div>
        )}
        {isPaidWaitlistCheckout && (
          <label className="checkout-waitlist-consent">
            <input
              checked={autoChargeConsent}
              type="checkbox"
              onChange={(event) => onAutoChargeConsentChange(event.target.checked)}
            />
            <span>
              If a spot opens for your whole party, Pickup Lane may charge this card up to{' '}
              {formatMoney(waitlistChargeCents)} after applying any available game credit.
              You won't be charged now, and leaving the waitlist before a spot opens costs nothing.
            </span>
          </label>
        )}
        {setupError && (
          <FormErrorMessage className="checkout-payment-error">
            {setupError}
          </FormErrorMessage>
        )}
        {stripeStatusMessage && (
          <p className="checkout-payment-note">{stripeStatusMessage}</p>
        )}
      </section>
    )
  }

  return (
    <section className="checkout-card">
      <h2>Payment method</h2>
      <div className="checkout-payment-row">
        <strong>{paymentMethod ? formatPaymentMethod(paymentMethod) : 'No in-app payment'}</strong>
        <span>Handled outside Pickup Lane</span>
      </div>
    </section>
  )
}
