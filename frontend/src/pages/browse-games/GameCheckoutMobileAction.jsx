import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'

export function GameCheckoutMobileAction({
  confirmDisabled,
  confirmLabel,
  onConfirmBooking,
}) {
  return (
    <div className="checkout-mobile-action">
      <button
        className="checkout-confirm-button"
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
    </div>
  )
}
