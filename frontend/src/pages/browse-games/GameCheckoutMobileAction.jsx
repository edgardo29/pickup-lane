import { CircleCheck } from 'lucide-react'
import { ShieldCheckIcon } from '../../components/BrowseIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'

export function GameCheckoutMobileAction({
  actionMessage,
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
        <CircleCheck aria-hidden="true" />
        <span>{confirmLabel}</span>
      </button>

      <FormErrorMessage className="checkout-action-error">
        {actionMessage}
      </FormErrorMessage>

      <p className="checkout-secure-note">
        <ShieldCheckIcon />
        Secure checkout
      </p>
    </div>
  )
}
