import { Link } from 'react-router-dom'
import { formatPaymentMethod } from './browseGameFormatters.js'

export function GameCheckoutPaymentCard({
  isStripeCheckout,
  onSelectPaymentMethod,
  paymentMethod,
  paymentMethods = [],
  selectedPaymentMethodId = '',
  stripeStatusMessage,
  stripeUnavailable,
}) {
  if (isStripeCheckout) {
    const hasSavedCards = paymentMethods.length > 0

    return (
      <section className="checkout-card">
        <div className="checkout-payment-heading">
          <h2>Payment</h2>
          <Link to="/settings/payment-methods">Manage cards</Link>
        </div>
        {stripeUnavailable && (
          <p className="checkout-payment-note checkout-payment-note--error">
            Secure payment is not configured.
          </p>
        )}
        {!stripeUnavailable && hasSavedCards && (
          <div className="checkout-payment-list">
            {paymentMethods.map((method) => (
              <label
                className="checkout-saved-card"
                key={method.id}
              >
                <input
                  checked={selectedPaymentMethodId === method.id}
                  name="checkout-payment-method"
                  onChange={() => onSelectPaymentMethod(method.id)}
                  type="radio"
                />
                <span>
                  <strong>{formatPaymentMethod(method)}</strong>
                  <small>
                    {method.is_default ? 'Default card' : 'Saved card'}
                    {' · '}
                    Expires {String(method.exp_month).padStart(2, '0')}/{method.exp_year}
                  </small>
                </span>
              </label>
            ))}
          </div>
        )}
        {!stripeUnavailable && !hasSavedCards && (
          <div className="checkout-payment-row checkout-payment-row--stacked">
            <strong>No saved card</strong>
            <span>Add a card from Settings to continue.</span>
          </div>
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
