import { formatPaymentMethod } from './browseGameFormatters.js'

export function GameCheckoutPaymentCard({ paymentMethod }) {
  return (
    <section className="checkout-card">
      <h2>Payment method</h2>
      <div className="checkout-payment-row">
        <strong>{paymentMethod ? formatPaymentMethod(paymentMethod) : 'Demo card .... 4242'}</strong>
        <span>Change payment coming soon</span>
      </div>
    </section>
  )
}
