import {
  Elements,
  PaymentElement,
  useElements,
  useStripe,
} from '@stripe/react-stripe-js'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppPageHeader } from '../../components/app/index.js'
import { hasStripePublishableKey, stripePromise } from '../../lib/stripe.js'
import {
  createPaymentMethodSetupIntent,
  listUserPaymentMethods,
  removePaymentMethod,
  setDefaultPaymentMethod,
  syncPaymentMethod,
} from '../../lib/paymentMethodsApi.js'
import { useAuth } from '../../hooks/useAuth.js'
import { capitalize } from './profileFormatters.js'
import { ProfileShell } from './ProfileShell.jsx'

const MAX_SAVED_PAYMENT_METHODS = 5

const PAYMENT_ELEMENT_OPTIONS = {
  layout: {
    type: 'accordion',
    defaultCollapsed: false,
    radios: 'never',
  },
  paymentMethodOrder: ['card'],
  wallets: {
    applePay: 'never',
    googlePay: 'never',
    link: 'never',
  },
}

function getRequestErrorMessage(error, fallbackMessage) {
  return error instanceof Error ? error.message : fallbackMessage
}

function getSetupErrorMessage(error) {
  const message = getRequestErrorMessage(error, 'Unable to save this card.')
  if (message === 'This card is already saved.') {
    return 'This card is already saved. Enter a different card.'
  }

  return message
}

function buildStripeElementsOptions(clientSecret) {
  return {
    clientSecret,
    appearance: {
      theme: 'night',
      variables: {
        colorPrimary: '#b8ff24',
        colorBackground: '#0c141d',
        colorText: '#f8fafc',
        colorDanger: '#ff6b73',
        borderRadius: '8px',
        fontFamily: 'Inter, system-ui, sans-serif',
      },
      rules: {
        '.Input': {
          border: '1px solid rgba(248, 250, 252, 0.16)',
        },
        '.Tab': {
          border: '1px solid rgba(248, 250, 252, 0.16)',
        },
        '.Tab--selected': {
          borderColor: '#b8ff24',
          color: '#f8fafc',
        },
      },
    },
  }
}

export function PaymentMethodsPage() {
  const { currentUser: firebaseUser } = useAuth()
  const [paymentMethods, setPaymentMethods] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [setupClientSecret, setSetupClientSecret] = useState('')
  const [setupError, setSetupError] = useState('')
  const [setupStatus, setSetupStatus] = useState('idle')
  const [activeMenuPaymentMethodId, setActiveMenuPaymentMethodId] = useState('')
  const [removeCandidate, setRemoveCandidate] = useState(null)
  const [removeStatus, setRemoveStatus] = useState('idle')
  const stripeReady = hasStripePublishableKey()
  const hasReachedSavedCardLimit = paymentMethods.length >= MAX_SAVED_PAYMENT_METHODS

  const loadPaymentMethods = useCallback(async () => {
    if (!firebaseUser) {
      return
    }

    setStatus('loading')
    setError('')

    try {
      const methods = await listUserPaymentMethods(firebaseUser)
      setPaymentMethods(methods)
      setStatus('success')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load payment methods.',
      )
      setStatus('error')
    }
  }, [firebaseUser])

  useEffect(() => {
    loadPaymentMethods()
  }, [loadPaymentMethods])

  async function createFreshSetupIntent() {
    if (!firebaseUser) {
      return null
    }

    return createPaymentMethodSetupIntent(
      firebaseUser,
      paymentMethods.length === 0,
    )
  }

  async function handleStartAddCard() {
    if (!firebaseUser || !stripeReady || hasReachedSavedCardLimit) {
      return
    }

    setSetupStatus('loading')
    setSetupError('')
    setSuccessMessage('')

    try {
      const setupIntent = await createFreshSetupIntent()
      if (!setupIntent) {
        throw new Error('Sign in to manage payment methods.')
      }

      setSetupClientSecret(setupIntent.client_secret)
      setSetupStatus('ready')
    } catch (requestError) {
      setSetupError(getRequestErrorMessage(requestError, 'Unable to start card setup.'))
      setSetupStatus('idle')
    }
  }

  async function handleSetupRejectedAfterStripeSuccess(requestError) {
    const errorMessage = getSetupErrorMessage(requestError)

    setSetupStatus('loading')
    setSetupError(errorMessage)

    try {
      const setupIntent = await createFreshSetupIntent()
      if (!setupIntent) {
        throw new Error('Sign in to manage payment methods.')
      }

      setSetupClientSecret(setupIntent.client_secret)
      setSetupError(errorMessage)
      setSetupStatus('ready')
    } catch (setupRequestError) {
      setSetupError(
        getRequestErrorMessage(
          setupRequestError,
          'Unable to reset the card form. Close this window and try again.',
        ),
      )
      setSetupStatus('idle')
    }
  }

  async function handleSetDefault(paymentMethodId) {
    if (!firebaseUser) {
      return
    }

    setError('')
    setSuccessMessage('')

    try {
      await setDefaultPaymentMethod(firebaseUser, paymentMethodId)
      await loadPaymentMethods()
      setActiveMenuPaymentMethodId('')
      setSuccessMessage('Default payment method updated.')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to update the default payment method.',
      )
    }
  }

  async function handleConfirmRemove() {
    if (!firebaseUser) {
      return
    }
    if (!removeCandidate) {
      return
    }

    setRemoveStatus('removing')
    setError('')
    setSuccessMessage('')

    try {
      await removePaymentMethod(firebaseUser, removeCandidate.id)
      await loadPaymentMethods()
      setRemoveCandidate(null)
      setActiveMenuPaymentMethodId('')
      setSuccessMessage('Payment method removed.')
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to remove this payment method.',
      )
    } finally {
      setRemoveStatus('idle')
    }
  }

  function handleCancelSetup() {
    setSetupClientSecret('')
    setSetupError('')
    setSetupStatus('idle')
  }

  return (
    <ProfileShell>
      <section className="settings-layout">
        <div className="settings-main">
          <div className="profile-subpage-heading">
            <Link className="settings-header-back" to="/settings">
              Back to settings
            </Link>
            <AppPageHeader
              title="Payment Methods"
              subtitle="Save cards for faster official game checkout."
            />
          </div>

          <section className="payment-methods-card">
            <div className="payment-methods-card__header">
              <div>
                <h2>Saved cards</h2>
              </div>
              <button
                className="profile-primary-action"
                disabled={
                  !stripeReady ||
                  setupStatus === 'loading' ||
                  Boolean(setupClientSecret) ||
                  hasReachedSavedCardLimit
                }
                onClick={handleStartAddCard}
                type="button"
              >
                {setupStatus === 'loading' ? 'Starting...' : 'Add card'}
              </button>
            </div>

            {!stripeReady && (
              <p className="payment-methods-alert payment-methods-alert--error">
                Stripe publishable key is not configured.
              </p>
            )}

            {error && <p className="payment-methods-alert payment-methods-alert--error">{error}</p>}
            {successMessage && <p className="payment-methods-alert">{successMessage}</p>}

            {status === 'loading' && <p className="payment-methods-empty">Loading saved cards...</p>}

            {status === 'success' && paymentMethods.length === 0 && (
              <p className="payment-methods-empty">No saved cards yet.</p>
            )}

            {status === 'success' && paymentMethods.length > 0 && (
              <div className="payment-methods-list">
                {paymentMethods.map((method) => (
                  <PaymentMethodRow
                    isMenuOpen={activeMenuPaymentMethodId === method.id}
                    key={method.id}
                    method={method}
                    onMenuToggle={() => {
                      setActiveMenuPaymentMethodId((currentId) => (
                        currentId === method.id ? '' : method.id
                      ))
                    }}
                    onRemove={() => {
                      setActiveMenuPaymentMethodId('')
                      setRemoveCandidate(method)
                    }}
                    onSetDefault={handleSetDefault}
                  />
                ))}
              </div>
            )}

          </section>
          {setupClientSecret && stripePromise && (
            <PaymentMethodSetupModal>
              <Elements
                key={setupClientSecret}
                options={buildStripeElementsOptions(setupClientSecret)}
                stripe={stripePromise}
              >
                <PaymentMethodSetupForm
                  firebaseUser={firebaseUser}
                  onCancel={handleCancelSetup}
                  onSaved={async () => {
                    setSetupClientSecret('')
                    setSetupStatus('idle')
                    await loadPaymentMethods()
                    setSuccessMessage('Card saved.')
                  }}
                  onSyncRejected={handleSetupRejectedAfterStripeSuccess}
                  setAsDefault={paymentMethods.length === 0}
                  setupClientSecret={setupClientSecret}
                  setSetupError={setSetupError}
                  setSetupStatus={setSetupStatus}
                  setupError={setupError}
                  setupStatus={setupStatus}
                />
              </Elements>
            </PaymentMethodSetupModal>
          )}
          {removeCandidate && (
            <RemovePaymentMethodModal
              method={removeCandidate}
              onCancel={() => setRemoveCandidate(null)}
              onConfirm={handleConfirmRemove}
              removeStatus={removeStatus}
            />
          )}
        </div>
      </section>
    </ProfileShell>
  )
}

function PaymentMethodRow({
  isMenuOpen,
  method,
  onMenuToggle,
  onRemove,
  onSetDefault,
}) {
  const label = `${capitalize(method.card_brand || 'card')} ending ${method.card_last4}`
  const expires = `${String(method.exp_month).padStart(2, '0')}/${method.exp_year}`

  return (
    <article className="payment-method-row">
      <div className="payment-method-row__mark" aria-hidden="true">
        {method.card_brand?.slice(0, 2).toUpperCase() || 'CC'}
      </div>
      <div>
        <h3>{label}</h3>
        <p>Expires {expires}</p>
      </div>
      {method.is_default && <span className="payment-method-row__badge">Default</span>}
      <div className="payment-method-row__actions">
        <button
          aria-expanded={isMenuOpen}
          aria-label={`Open actions for ${label}`}
          className="payment-method-row__menu-trigger"
          type="button"
          onClick={onMenuToggle}
        >
          <PaymentMethodMenuIcon />
        </button>
        {isMenuOpen && (
          <div className="payment-method-row__menu" role="menu">
            {!method.is_default && (
              <button
                role="menuitem"
                type="button"
                onClick={() => onSetDefault(method.id)}
              >
                Make default
              </button>
            )}
            <button
              className="payment-method-row__menu-remove"
              role="menuitem"
              type="button"
              onClick={onRemove}
            >
              Remove card
            </button>
          </div>
        )}
      </div>
    </article>
  )
}

function PaymentMethodMenuIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="6" cy="12" r="1.7" />
      <circle cx="12" cy="12" r="1.7" />
      <circle cx="18" cy="12" r="1.7" />
    </svg>
  )
}

function PaymentMethodSetupModal({ children }) {
  return (
    <div
      aria-labelledby="add-payment-method-title"
      aria-modal="true"
      className="settings-modal"
      role="dialog"
    >
      <div className="settings-modal__card settings-modal__card--neutral payment-method-setup-modal">
        <div>
          <h2 id="add-payment-method-title">Add card</h2>
          <p>Card details are handled by Stripe.</p>
        </div>
        {children}
      </div>
    </div>
  )
}

function RemovePaymentMethodModal({
  method,
  onCancel,
  onConfirm,
  removeStatus,
}) {
  const label = `${capitalize(method.card_brand || 'card')} ending ${method.card_last4}`
  const isRemoving = removeStatus === 'removing'

  return (
    <div
      aria-labelledby="remove-payment-method-title"
      aria-modal="true"
      className="settings-modal"
      role="dialog"
    >
      <div className="settings-modal__card">
        <div>
          <h2 id="remove-payment-method-title">Remove card?</h2>
          <p>{label} will no longer be available for official game checkout.</p>
        </div>
        <div className="settings-modal__actions">
          <button
            className="profile-edit-cancel"
            disabled={isRemoving}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
          <button
            className="profile-primary-action profile-primary-action--danger"
            disabled={isRemoving}
            onClick={onConfirm}
            type="button"
          >
            {isRemoving ? 'Removing...' : 'Remove card'}
          </button>
        </div>
      </div>
    </div>
  )
}

function PaymentMethodSetupForm({
  firebaseUser,
  onCancel,
  onSaved,
  onSyncRejected,
  setAsDefault,
  setupClientSecret,
  setSetupError,
  setSetupStatus,
  setupError,
  setupStatus,
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

      try {
        await syncPaymentMethod(firebaseUser, { setupIntentId, setAsDefault })
      } catch (syncError) {
        await onSyncRejected(syncError)
        return
      }

      await onSaved()
    } catch (requestError) {
      setSetupError(getRequestErrorMessage(requestError, 'Unable to save this card.'))
      setSetupStatus('ready')
    }
  }

  return (
    <form className="payment-method-setup" onSubmit={handleSubmit}>
      <PaymentElement
        onChange={(event) => setPaymentComplete(Boolean(event.complete))}
        options={PAYMENT_ELEMENT_OPTIONS}
      />
      {setupError && (
        <p className="payment-methods-alert payment-methods-alert--error">{setupError}</p>
      )}
      <div className="payment-method-setup__actions">
        <button className="profile-edit-cancel" onClick={onCancel} type="button">
          Cancel
        </button>
        <button
          className="profile-primary-action"
          disabled={!stripe || !elements || !paymentComplete || setupStatus !== 'ready'}
          type="submit"
        >
          {setupStatus === 'saving' ? 'Saving...' : 'Save card'}
        </button>
      </div>
    </form>
  )
}
