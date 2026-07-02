import { Elements } from '@stripe/react-stripe-js'
import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ArrowLeftIcon } from '../../components/AuthIcons.jsx'
import { AppPageHeader } from '../../components/app/index.js'
import {
  PaymentMethodSetupDialog,
  PaymentMethodSetupForm,
} from '../../features/payment-methods/PaymentMethodSetupDialog.jsx'
import {
  buildStripeElementsOptions,
  getRequestErrorMessage,
  getSetupErrorMessage,
} from '../../features/payment-methods/paymentMethodSetup.js'
import { hasStripePublishableKey, stripePromise } from '../../lib/stripe.js'
import {
  createPaymentMethodSetupIntent,
  listUserPaymentMethods,
  removePaymentMethod,
  setDefaultPaymentMethod,
} from '../../lib/paymentMethodsApi.js'
import { useAuth } from '../../hooks/useAuth.js'
import { PaymentCardIcon } from './ProfileIcons.jsx'
import { capitalize } from './profileFormatters.js'
import { ProfileShell } from './ProfileShell.jsx'
import {
  dismissOnBackdropMouseDown,
  useDismissibleModal,
} from '../../hooks/useDismissibleModal.js'

const MAX_SAVED_PAYMENT_METHODS = 5

function getSafeReturnPath(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) {
    return ''
  }

  return value
}

export function PaymentMethodsPage() {
  const { currentUser: firebaseUser } = useAuth()
  const location = useLocation()
  const searchParams = new URLSearchParams(location.search)
  const returnTo = getSafeReturnPath(searchParams.get('returnTo'))
  const backTo = returnTo || '/profile'
  const backLabel = returnTo ? 'Back to checkout' : 'Back to profile'
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
    const timerId = window.setTimeout(() => {
      loadPaymentMethods()
    }, 0)

    return () => window.clearTimeout(timerId)
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
      <section className="settings-layout settings-layout--payment-methods">
        <div className="settings-main settings-main--payment-methods">
          <div className="profile-subpage-heading profile-subpage-heading--with-action">
            <AppPageHeader
              title="Payment Methods"
              subtitle="Save cards for faster official game checkout."
            />
            <Link className="settings-header-back app-back-control" to={backTo} aria-label={backLabel}>
              <span className="app-back-control__icon">
                <ArrowLeftIcon />
              </span>
              <span>Back</span>
            </Link>
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
            {successMessage && (
              <p className="payment-methods-alert payment-methods-alert--inline">
                <span>{successMessage}</span>
                {returnTo && <Link to={returnTo}>Return to checkout</Link>}
              </p>
            )}

            {status === 'loading' && (
              <PaymentMethodsEmptyState title="Loading saved cards..." />
            )}

            {status === 'success' && paymentMethods.length === 0 && (
              <PaymentMethodsEmptyState
                title="No saved cards yet"
                message="Add a card to speed up official game checkout."
              />
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
            <PaymentMethodSetupDialog>
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
                  cancelButtonClassName="profile-edit-cancel"
                  cancelLabel="Back"
                  primaryButtonClassName="profile-primary-action"
                />
              </Elements>
            </PaymentMethodSetupDialog>
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

function PaymentMethodsEmptyState({ message = '', title }) {
  return (
    <div className="payment-methods-empty">
      <PaymentCardIcon />
      <strong>{title}</strong>
      {message && <span>{message}</span>}
    </div>
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

function RemovePaymentMethodModal({
  method,
  onCancel,
  onConfirm,
  removeStatus,
}) {
  const label = `${capitalize(method.card_brand || 'card')} ending ${method.card_last4}`
  const isRemoving = removeStatus === 'removing'
  const handleCancel = () => {
    if (!isRemoving) {
      onCancel()
    }
  }

  useDismissibleModal(handleCancel)

  return (
    <div
      aria-labelledby="remove-payment-method-title"
      aria-modal="true"
      className="settings-modal"
      role="dialog"
      onMouseDown={(event) => dismissOnBackdropMouseDown(event, handleCancel)}
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
            onClick={handleCancel}
            type="button"
          >
            Back
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
