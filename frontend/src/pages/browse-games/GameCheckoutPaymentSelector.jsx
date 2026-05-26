import { useEffect, useRef } from 'react'
import {
  formatPaymentMethodExpiration,
  isPaymentMethodExpired,
} from '../../lib/paymentMethodCards.js'
import { formatPaymentMethod } from './browseGameFormatters.js'

export function GameCheckoutPaymentSelector({
  canAddPaymentMethod = true,
  onAddNewCard,
  onClose,
  onSelectPaymentMethod,
  paymentMethods = [],
  selectedPaymentMethodId = '',
}) {
  const dialogRef = useRef(null)
  const previousFocusRef = useRef(null)

  useEffect(() => {
    previousFocusRef.current = document.activeElement

    const firstButton = dialogRef.current?.querySelector('button:not(:disabled)')
    firstButton?.focus()

    return () => {
      previousFocusRef.current?.focus?.()
    }
  }, [])

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      aria-labelledby="checkout-payment-selector-title"
      aria-modal="true"
      className="checkout-payment-selector-backdrop"
      role="dialog"
    >
      <section className="checkout-payment-selector" ref={dialogRef}>
        <div className="checkout-payment-selector__header">
          <div>
            <h2 id="checkout-payment-selector-title">Choose payment method</h2>
            <p>Select a saved card for this booking.</p>
          </div>
          <button
            aria-label="Close payment method selector"
            className="checkout-payment-selector__close"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>

        <div className="checkout-payment-selector__list">
          {paymentMethods.map((method) => (
            <PaymentSelectorRow
              isSelected={method.id === selectedPaymentMethodId}
              key={method.id}
              method={method}
              onSelectPaymentMethod={onSelectPaymentMethod}
            />
          ))}
        </div>

        <button
          className="checkout-payment-selector__add"
          disabled={!canAddPaymentMethod}
          onClick={onAddNewCard}
          type="button"
        >
          Add new card
        </button>
      </section>
    </div>
  )
}

function PaymentSelectorRow({
  isSelected,
  method,
  onSelectPaymentMethod,
}) {
  const isExpired = isPaymentMethodExpired(method)
  const expiration = formatPaymentMethodExpiration(method)
  const statusLabel = getStatusLabel({ isExpired, isSelected, method })

  return (
    <div
      className={`checkout-payment-selector-row${
        isSelected ? ' checkout-payment-selector-row--selected' : ''
      }${isExpired ? ' checkout-payment-selector-row--expired' : ''}`}
    >
      <div className="checkout-payment-selector-row__copy">
        <strong>{formatPaymentMethod(method)}</strong>
        <span>
          {statusLabel}
          {' · '}
          {isExpired ? 'Expired' : 'Expires'} {expiration}
        </span>
      </div>
      <button
        disabled={isSelected || isExpired}
        onClick={() => onSelectPaymentMethod(method.id)}
        type="button"
      >
        {isSelected ? 'Selected' : 'Use this card'}
      </button>
    </div>
  )
}

function getStatusLabel({ isExpired, isSelected, method }) {
  if (isExpired) {
    return 'Unavailable'
  }

  if (isSelected) {
    return 'Selected'
  }

  return method.is_default ? 'Default card' : 'Saved card'
}
