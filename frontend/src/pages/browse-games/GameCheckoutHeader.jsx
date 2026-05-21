export function GameCheckoutHeader({
  isAddGuestsCheckout,
  isWaitlistCheckout,
  onBack,
}) {
  return (
    <header className="checkout-header">
      <button className="checkout-back" type="button" onClick={onBack}>
        ←
      </button>
      <div>
        <span>
          {isAddGuestsCheckout
            ? 'Guest checkout'
            : isWaitlistCheckout
              ? 'Waitlist checkout'
              : 'Game checkout'}
        </span>
        <h1>
          {isAddGuestsCheckout
            ? 'Add Guests'
            : isWaitlistCheckout
              ? 'Join Waitlist'
              : 'Confirm Spot'}
        </h1>
      </div>
    </header>
  )
}
