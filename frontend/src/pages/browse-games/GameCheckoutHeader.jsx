import { ArrowLeft } from 'lucide-react'

export function GameCheckoutHeader({
  isAddGuestsCheckout,
  isWaitlistCheckout,
  onBack,
}) {
  const title = isAddGuestsCheckout
    ? 'Add Guests'
    : isWaitlistCheckout
      ? 'Join Waitlist'
      : 'Confirm Spot'

  return (
    <header className="checkout-header">
      <button className="checkout-back" type="button" onClick={onBack}>
        <ArrowLeft aria-hidden="true" />
        <span>Back</span>
      </button>
      <h1>{title}</h1>
    </header>
  )
}
