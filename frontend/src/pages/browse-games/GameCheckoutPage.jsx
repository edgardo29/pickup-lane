import { Elements } from '@stripe/react-stripe-js'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import {
  PaymentMethodSetupDialog,
  PaymentMethodSetupForm,
} from '../../features/payment-methods/PaymentMethodSetupDialog.jsx'
import { LegalPolicyModal } from '../../features/legal/LegalPolicyModal.jsx'
import {
  buildStripeElementsOptions,
  getRequestErrorMessage,
  getSetupErrorMessage,
} from '../../features/payment-methods/paymentMethodSetup.js'
import GameCheckoutLayout from './GameCheckoutLayout.jsx'
import { GameCheckoutPaymentSelector } from './GameCheckoutPaymentSelector.jsx'
import { buildGameCheckoutViewModel } from './gameCheckoutViewModel.js'
import { useGameCheckoutActions } from './useGameCheckoutActions.js'
import { useGameCheckoutData } from './useGameCheckoutData.js'
import { useAuth } from '../../hooks/useAuth.js'
import { createPaymentMethodSetupIntent } from '../../lib/paymentMethodsApi.js'
import {
  getPreferredPaymentMethod,
  getUsablePaymentMethods,
} from '../../lib/paymentMethodCards.js'
import { hasStripePublishableKey, stripePromise } from '../../lib/stripe.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/browse-games/GameCheckoutPage.css'

const MAX_SAVED_PAYMENT_METHODS = 5

function GameCheckoutPage() {
  const { gameId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { appUser, currentUser: firebaseUser, isLoading: isAuthLoading } = useAuth()
  const isAddGuestsCheckout = searchParams.get('mode') === 'add-guests'
  const requestedGuestCount = Number.parseInt(searchParams.get('guest_count') || '', 10)

  const [guestCount, setGuestCount] = useState(() => (
    isAddGuestsCheckout && Number.isFinite(requestedGuestCount)
      ? Math.max(requestedGuestCount, 1)
      : 0
  ))
  const [agreed, setAgreed] = useState(false)
  const [selectedPaymentMethodId, setSelectedPaymentMethodId] = useState('')
  const [setupClientSecret, setSetupClientSecret] = useState('')
  const [setupError, setSetupError] = useState('')
  const [setupStatus, setSetupStatus] = useState('idle')
  const [useNewCardAsDefault, setUseNewCardAsDefault] = useState(false)
  const [isPaymentSelectorOpen, setIsPaymentSelectorOpen] = useState(false)
  const [activeLegalPolicyId, setActiveLegalPolicyId] = useState('')
  const [checkoutActionError, setCheckoutActionError] = useState('')
  const [nowMs, setNowMs] = useState(null)

  useEffect(() => {
    function updateNow() {
      setNowMs(Date.now())
    }

    updateNow()
    const intervalId = window.setInterval(updateNow, 30000)

    return () => window.clearInterval(intervalId)
  }, [])
  const checkoutData = useGameCheckoutData({
    appUser,
    firebaseUser,
    gameId,
    isAuthLoading,
    navigate,
  })
  const {
    confirmBooking,
    isSubmitting,
    prepareStripeCheckout,
    resetSubmitError,
    resetStripeCheckout,
    stripeCheckout,
    stripeStatusMessage,
    submitError,
  } = useGameCheckoutActions({ navigate })
  const selectedPaymentMethodIsUsable = getUsablePaymentMethods(checkoutData.paymentMethods)
    .some((method) => method.id === selectedPaymentMethodId)
  const effectiveSelectedPaymentMethodId = selectedPaymentMethodIsUsable
    ? selectedPaymentMethodId
    : getPreferredPaymentMethod(checkoutData.paymentMethods)?.id || ''
  const checkout = buildGameCheckoutViewModel({
    appUser,
    game: checkoutData.game,
    guestCount,
    images: checkoutData.images,
    isAddGuestsCheckout,
    isSubmitting,
    nowMs,
    participants: checkoutData.participants,
    paymentMethods: checkoutData.paymentMethods,
    selectedPaymentMethodId: effectiveSelectedPaymentMethodId,
    venue: checkoutData.venue,
  })

  useEffect(() => {
    resetSubmitError()
    resetStripeCheckout()
  }, [appUser?.id, gameId, isAddGuestsCheckout, resetStripeCheckout, resetSubmitError])

  async function createFreshSetupIntent(setAsDefault) {
    if (!firebaseUser) {
      return null
    }

    return createPaymentMethodSetupIntent(firebaseUser, setAsDefault)
  }

  async function handleStartAddCard() {
    if (setupStatus === 'loading' || setupClientSecret) {
      return
    }

    if (checkoutData.paymentMethods.length >= MAX_SAVED_PAYMENT_METHODS) {
      setSetupError(`You can save up to ${MAX_SAVED_PAYMENT_METHODS} active cards.`)
      return
    }

    if (!firebaseUser || !hasStripePublishableKey()) {
      return
    }

    const shouldSetDefault = checkoutData.paymentMethods.length === 0
    setSetupStatus('loading')
    setSetupError('')
    setCheckoutActionError('')
    setUseNewCardAsDefault(false)

    try {
      const setupIntent = await createFreshSetupIntent(shouldSetDefault)
      if (!setupIntent) {
        throw new Error('Sign in to add a card.')
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
    const shouldSetDefault = checkoutData.paymentMethods.length === 0 || useNewCardAsDefault

    setSetupStatus('loading')
    setSetupError(errorMessage)

    try {
      const setupIntent = await createFreshSetupIntent(shouldSetDefault)
      if (!setupIntent) {
        throw new Error('Sign in to add a card.')
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

  function handleCancelSetup() {
    setSetupClientSecret('')
    setSetupError('')
    setSetupStatus('idle')
    setUseNewCardAsDefault(false)
  }

  async function handleCardSaved(paymentMethod) {
    setSetupClientSecret('')
    setSetupError('')
    setSetupStatus('idle')
    setUseNewCardAsDefault(false)
    setIsPaymentSelectorOpen(false)
    setCheckoutActionError('')

    const nextPaymentMethods = await checkoutData.reloadPaymentMethods()
    const savedPaymentMethod =
      nextPaymentMethods.find((method) => method.id === paymentMethod?.id) ||
      nextPaymentMethods[0] ||
      paymentMethod

    if (savedPaymentMethod?.id) {
      setSelectedPaymentMethodId(savedPaymentMethod.id)
    }
  }

  function handleOpenPaymentSelector() {
    setSetupError('')
    setCheckoutActionError('')
    setIsPaymentSelectorOpen(true)
  }

  function handleSelectPaymentMethod(paymentMethodId) {
    setSelectedPaymentMethodId(paymentMethodId)
    setIsPaymentSelectorOpen(false)
    setCheckoutActionError('')
    resetStripeCheckout()
  }

  function handleAgreementChange(nextAgreed) {
    setAgreed(nextAgreed)
    setCheckoutActionError('')
  }

  async function handleAddCardFromSelector() {
    setIsPaymentSelectorOpen(false)
    await handleStartAddCard()
  }

  if (checkoutData.status === 'loading') {
    return (
      <div className="checkout-page">
        <BrowseAppNav />
        <main className="checkout-shell checkout-state">Loading checkout...</main>
      </div>
    )
  }

  if (checkoutData.status === 'error' || !checkoutData.game) {
    return (
      <div className="checkout-page">
        <BrowseAppNav />
        <main className="checkout-shell checkout-state">
          <h1>Checkout unavailable</h1>
          <p>{checkoutData.error || 'This game could not be loaded.'}</p>
          <Link to={`/games/${gameId}`}>Back to game</Link>
        </main>
      </div>
    )
  }

  const isStripeCheckout = Boolean(
    checkoutData.game?.game_type === 'official' &&
      checkoutData.game?.payment_collection_type === 'in_app' &&
      !checkout.isWaitlistCheckout &&
      !isAddGuestsCheckout,
  )
  const isStripeReady = hasStripePublishableKey()
  const hasReachedSavedCardLimit = checkoutData.paymentMethods.length >= MAX_SAVED_PAYMENT_METHODS
  const canAddPaymentMethod = isStripeReady && !hasReachedSavedCardLimit && setupStatus !== 'loading'
  const selectedUsablePaymentMethod = getUsablePaymentMethods(checkoutData.paymentMethods)
    .find((method) => method.id === effectiveSelectedPaymentMethodId)
  const usesSavedPaymentMethod = Boolean(isStripeCheckout && selectedUsablePaymentMethod)
  const stripeUnavailable = isStripeCheckout && !isStripeReady
  const isExistingParticipantBlocked = Boolean(
    !isAddGuestsCheckout &&
      checkout.existingParticipant &&
      !checkout.isPaymentResume,
  )
  const isGuestSelectionLocked = Boolean(
    isStripeCheckout &&
      (stripeCheckout?.client_secret || checkout.isPaymentResume),
  )
  const confirmLabel = getConfirmLabel({
    isAddGuestsCheckout,
    isWaitlistCheckout: checkout.isWaitlistCheckout,
    isSubmitting,
  })
  const checkoutActionMessage = checkoutActionError

  const handleConfirm = async () => {
    if (!agreed) {
      setCheckoutActionError('')
      return
    }

    if (isStripeCheckout) {
      if (!usesSavedPaymentMethod) {
        setCheckoutActionError('Add a payment method to continue.')
        return
      }

      if (stripeUnavailable) {
        setCheckoutActionError('Secure payment is not configured.')
        return
      }

      setCheckoutActionError('')
      await prepareStripeCheckout({
        agreed,
        appUser,
        effectiveGuestCount: checkout.effectiveGuestCount,
        existingParticipant: checkout.existingParticipant,
        firebaseUser,
        game: checkoutData.game,
        isJoinWindowClosed: checkout.isJoinWindowClosed,
        isPaymentResume: checkout.isPaymentResume,
        paymentMethodId: effectiveSelectedPaymentMethodId,
        returnUrl: `${window.location.origin}/games/${checkoutData.game.id}/checkout`,
        stripePromise,
      })
      return
    }

    setCheckoutActionError('')
    confirmBooking({
      agreed,
      appUser,
      effectiveGuestCount: checkout.effectiveGuestCount,
      existingParticipant: checkout.existingParticipant,
      firebaseUser,
      game: checkoutData.game,
      isAddGuestsCheckout,
      isJoinWindowClosed: checkout.isJoinWindowClosed,
    })
  }
  const renderLayout = () => (
    <GameCheckoutLayout
      address={checkout.address}
      agreed={agreed}
      appUser={appUser}
      checkoutActionMessage={checkoutActionMessage}
      confirmLabel={confirmLabel}
      effectiveGuestCount={checkout.effectiveGuestCount}
      existingParticipant={checkout.existingParticipant}
      game={checkoutData.game}
      isAddGuestsBlockedByParticipant={checkout.isAddGuestsBlockedByParticipant}
      isAddGuestsCheckout={isAddGuestsCheckout}
      isBlockedByCapacity={checkout.isBlockedByCapacity}
      isExistingParticipantBlocked={isExistingParticipantBlocked}
      isGuestSelectionLocked={isGuestSelectionLocked}
      isJoinWindowClosed={checkout.isJoinWindowClosed}
      isSubmitting={isSubmitting}
      isStripeCheckout={isStripeCheckout}
      isStripeReady={isStripeReady}
      isWaitlistCheckout={checkout.isWaitlistCheckout}
      maxGuests={checkout.maxGuests}
      maxSelectableGuests={checkout.maxSelectableGuests}
      minGuestCount={checkout.minGuestCount}
      canAddPaymentMethod={canAddPaymentMethod}
      onBack={() => navigate(`/games/${checkoutData.game.id}`)}
      onAddPaymentMethod={handleStartAddCard}
      onChangePaymentMethod={handleOpenPaymentSelector}
      onConfirmBooking={handleConfirm}
      onGuestCountChange={(nextGuestCount) => {
        setGuestCount(nextGuestCount)
        resetStripeCheckout()
      }}
      onOpenLegalPolicy={setActiveLegalPolicyId}
      onSetAgreed={handleAgreementChange}
      paymentMethod={checkout.paymentMethod}
      paymentMethods={checkout.paymentMethods}
      platformFee={checkout.platformFee}
      price={checkout.price}
      primaryImage={checkout.primaryImage}
      projectedGuestCount={checkout.projectedGuestCount}
      setupError={!setupClientSecret ? setupError : ''}
      submitError={submitError}
      stripeStatusMessage={stripeStatusMessage}
      stripeUnavailable={stripeUnavailable}
      title={checkout.title}
      total={checkout.total}
    />
  )

  return (
    <>
      {renderLayout()}
      {isPaymentSelectorOpen && isStripeCheckout && checkoutData.paymentMethods.length > 0 && (
        <GameCheckoutPaymentSelector
          canAddPaymentMethod={canAddPaymentMethod}
          onAddNewCard={handleAddCardFromSelector}
          onClose={() => setIsPaymentSelectorOpen(false)}
          onSelectPaymentMethod={handleSelectPaymentMethod}
          paymentMethods={checkoutData.paymentMethods}
          selectedPaymentMethodId={effectiveSelectedPaymentMethodId}
        />
      )}
      {setupClientSecret && stripePromise && (
        <PaymentMethodSetupDialog
          description="Save a card for this checkout."
          title="Add card"
        >
          <Elements
            key={setupClientSecret}
            options={buildStripeElementsOptions(setupClientSecret)}
            stripe={stripePromise}
          >
            <PaymentMethodSetupForm
              cancelButtonClassName="checkout-modal-button checkout-modal-button--secondary"
              defaultOption={
                checkoutData.paymentMethods.length > 0 ? (
                  <label className="payment-method-setup-form__default">
                    <input
                      checked={useNewCardAsDefault}
                      type="checkbox"
                      onChange={(event) => setUseNewCardAsDefault(event.target.checked)}
                    />
                    <span>Use this card as my default for future games</span>
                  </label>
                ) : null
              }
              firebaseUser={firebaseUser}
              onCancel={handleCancelSetup}
              onSaved={handleCardSaved}
              onSyncRejected={handleSetupRejectedAfterStripeSuccess}
              primaryButtonClassName="checkout-modal-button checkout-modal-button--primary"
              setAsDefault={checkoutData.paymentMethods.length === 0 || useNewCardAsDefault}
              setupClientSecret={setupClientSecret}
              setSetupError={setSetupError}
              setSetupStatus={setSetupStatus}
              setupError={setupError}
              setupStatus={setupStatus}
            />
          </Elements>
        </PaymentMethodSetupDialog>
      )}
      {activeLegalPolicyId && (
        <LegalPolicyModal
          policyId={activeLegalPolicyId}
          onClose={() => setActiveLegalPolicyId('')}
        />
      )}
    </>
  )
}

function getConfirmLabel({
  isAddGuestsCheckout,
  isWaitlistCheckout,
  isSubmitting,
}) {
  if (isSubmitting) {
    return 'Confirming...'
  }

  if (isAddGuestsCheckout) {
    return 'Confirm Guests'
  }

  return isWaitlistCheckout ? 'Join Waitlist' : 'Confirm Spot'
}

export default GameCheckoutPage
