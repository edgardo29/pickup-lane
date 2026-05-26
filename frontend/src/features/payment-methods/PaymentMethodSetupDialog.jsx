import {
  PaymentElement,
  useElements,
  useStripe,
} from '@stripe/react-stripe-js'
import { useState } from 'react'
import { syncPaymentMethod } from '../../lib/paymentMethodsApi.js'
import {
  getRequestErrorMessage,
  PAYMENT_ELEMENT_OPTIONS,
} from './paymentMethodSetup.js'
import './PaymentMethodSetupDialog.css'

export function PaymentMethodSetupDialog({
  children,
  description = 'Card details are handled by Stripe.',
  title = 'Add card',
}) {
  return (
    <div
      aria-labelledby="payment-method-setup-title"
      aria-modal="true"
      className="payment-method-setup-backdrop"
      role="dialog"
    >
      <section className="payment-method-setup-card">
        <div className="payment-method-setup-card__copy">
          <h2 id="payment-method-setup-title">{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {children}
      </section>
    </div>
  )
}

export function PaymentMethodSetupForm({
  cancelButtonClassName = '',
  cancelLabel = 'Cancel',
  defaultOption = null,
  firebaseUser,
  onCancel,
  onSaved,
  onSyncRejected,
  primaryButtonClassName = '',
  setAsDefault,
  setupClientSecret,
  setSetupError,
  setSetupStatus,
  setupError,
  setupStatus,
  submitLabel = 'Save card',
}) {
  const stripe = useStripe()
  const elements = useElements()
  const [paymentComplete, setPaymentComplete] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()

    if (!stripe || !elements || !firebaseUser) {
      return
    }

    setSetupStatus('saving')
    setSetupError('')

    try {
      const submitResult = await elements.submit()

      if (submitResult.error) {
        throw new Error(submitResult.error.message || 'Card setup could not be completed.')
      }

      const confirmResult = await stripe.confirmSetup({
        elements,
        clientSecret: setupClientSecret,
        confirmParams: {
          return_url: window.location.href,
        },
        redirect: 'if_required',
      })

      if (confirmResult.error) {
        throw new Error(confirmResult.error.message || 'Card setup could not be completed.')
      }

      const setupIntentId = confirmResult.setupIntent?.id
      if (!setupIntentId) {
        throw new Error('Stripe did not return a completed setup intent.')
      }

      let paymentMethod = null
      try {
        paymentMethod = await syncPaymentMethod(firebaseUser, { setupIntentId, setAsDefault })
      } catch (syncError) {
        await onSyncRejected(syncError)
        return
      }

      await onSaved(paymentMethod)
    } catch (requestError) {
      setSetupError(getRequestErrorMessage(requestError, 'Unable to save this card.'))
      setSetupStatus('ready')
    }
  }

  return (
    <form className="payment-method-setup-form" onSubmit={handleSubmit}>
      <div className="payment-method-setup-form__element">
        <PaymentElement
          onChange={(event) => setPaymentComplete(Boolean(event.complete))}
          options={PAYMENT_ELEMENT_OPTIONS}
        />
      </div>
      {defaultOption}
      {setupError && (
        <p className="payment-method-setup-form__error">{setupError}</p>
      )}
      <div className="payment-method-setup-form__actions">
        <button className={cancelButtonClassName} onClick={onCancel} type="button">
          {cancelLabel}
        </button>
        <button
          className={primaryButtonClassName}
          disabled={!stripe || !elements || !paymentComplete || setupStatus !== 'ready'}
          type="submit"
        >
          {setupStatus === 'saving' ? 'Saving...' : submitLabel}
        </button>
      </div>
    </form>
  )
}
