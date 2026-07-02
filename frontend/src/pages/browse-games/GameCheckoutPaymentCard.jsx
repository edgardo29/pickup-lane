import { CreditCard } from 'lucide-react'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  formatPaymentMethodExpiration,
  isPaymentMethodExpired,
} from '../../lib/paymentMethodCards.js'
import { formatPaymentMethod } from './browseGameFormatters.js'

export function GameCheckoutPaymentCard({
  canAddPaymentMethod = true,
  isStripeCheckout,
  onAddPaymentMethod,
  onChangePaymentMethod,
  paymentMethod,
  paymentMethods = [],
  setupError = '',
  stripeStatusMessage,
  stripeUnavailable,
}) {
  if (isStripeCheckout) {
    const hasSavedCards = paymentMethods.length > 0
    const selectedCardIsExpired = isPaymentMethodExpired(paymentMethod)

    return (
      <section className="checkout-card">
        <div className="checkout-payment-heading">
          <h2>Payment</h2>
          {hasSavedCards && (
            <button
              className="checkout-payment-change"
              onClick={onChangePaymentMethod}
              type="button"
            >
              Change
            </button>
          )}
        </div>
        {stripeUnavailable && (
          <FormErrorMessage className="checkout-payment-error">
            Secure payment is not configured.
          </FormErrorMessage>
        )}
        {!stripeUnavailable && hasSavedCards && paymentMethod && (
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
        {!stripeUnavailable && !hasSavedCards && (
          <div className="checkout-payment-empty">
            <div>
              <strong>No payment method</strong>
              <span>Add a card to reserve your spot.</span>
            </div>
            <button disabled={!canAddPaymentMethod} type="button" onClick={onAddPaymentMethod}>
              <CreditCard aria-hidden="true" />
              <span>Add card</span>
            </button>
          </div>
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
