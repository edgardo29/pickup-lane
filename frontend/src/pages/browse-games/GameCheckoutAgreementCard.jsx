import { Link } from 'react-router-dom'

export function GameCheckoutAgreementCard({ agreed, onSetAgreed }) {
  return (
    <label className="checkout-card checkout-agree">
      <input checked={agreed} type="checkbox" onChange={(event) => onSetAgreed(event.target.checked)} />
      <span>
        I agree to the Pickup Lane <Link to="/terms">Terms of Service</Link> and{' '}
        <Link to="/policies/cancellation-refunds">refund policy</Link>.
      </span>
    </label>
  )
}
