import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import GameCheckoutLayout from './GameCheckoutLayout.jsx'
import { buildGameCheckoutViewModel } from './gameCheckoutViewModel.js'
import { useGameCheckoutActions } from './useGameCheckoutActions.js'
import { useGameCheckoutData } from './useGameCheckoutData.js'
import { useAuth } from '../../hooks/useAuth.js'
import { hasStripePublishableKey, stripePromise } from '../../lib/stripe.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/browse-games/GameCheckoutPage.css'

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
  const checkout = buildGameCheckoutViewModel({
    agreed,
    appUser,
    game: checkoutData.game,
    guestCount,
    images: checkoutData.images,
    isAddGuestsCheckout,
    isSubmitting,
    nowMs,
    participants: checkoutData.participants,
    paymentMethods: checkoutData.paymentMethods,
    selectedPaymentMethodId,
    venue: checkoutData.venue,
  })

  useEffect(() => {
    resetSubmitError()
    resetStripeCheckout()
  }, [appUser?.id, gameId, isAddGuestsCheckout, resetStripeCheckout, resetSubmitError])

  useEffect(() => {
    const paymentMethods = checkoutData.paymentMethods
    if (paymentMethods.length === 0) {
      if (selectedPaymentMethodId) {
        setSelectedPaymentMethodId('')
      }
      return
    }

    const selectedMethodExists = paymentMethods.some(
      (method) => method.id === selectedPaymentMethodId,
    )
    if (!selectedMethodExists) {
      const nextMethod = paymentMethods.find((method) => method.is_default) || paymentMethods[0]
      setSelectedPaymentMethodId(nextMethod.id)
    }
  }, [checkoutData.paymentMethods, selectedPaymentMethodId])

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
  const usesSavedPaymentMethod = Boolean(isStripeCheckout && selectedPaymentMethodId)
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
  const isPaymentActionBlocked = Boolean(
    stripeUnavailable ||
      (isStripeCheckout && !usesSavedPaymentMethod),
  )
  const confirmLabel = getConfirmLabel({
    fallbackLabel: checkout.confirmLabel,
    isStripeCheckout,
    isStripeReady,
    isSubmitting,
    usesSavedPaymentMethod,
    agreed,
  })
  const handleConfirm = async () => {
    if (isStripeCheckout) {
      if (!usesSavedPaymentMethod) {
        return
      }

      await prepareStripeCheckout({
        agreed,
        appUser,
        effectiveGuestCount: checkout.effectiveGuestCount,
        existingParticipant: checkout.existingParticipant,
        firebaseUser,
        game: checkoutData.game,
        isJoinWindowClosed: checkout.isJoinWindowClosed,
        isPaymentResume: checkout.isPaymentResume,
        paymentMethodId: selectedPaymentMethodId,
        returnUrl: `${window.location.origin}/games/${checkoutData.game.id}/checkout`,
        stripePromise,
      })
      return
    }

    confirmBooking({
      agreed,
      appUser,
      effectiveGuestCount: checkout.effectiveGuestCount,
      existingParticipant: checkout.existingParticipant,
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
      isPaymentActionBlocked={isPaymentActionBlocked}
      isSubmitting={isSubmitting}
      isStripeCheckout={isStripeCheckout}
      isWaitlistCheckout={checkout.isWaitlistCheckout}
      maxGuests={checkout.maxGuests}
      maxSelectableGuests={checkout.maxSelectableGuests}
      minGuestCount={checkout.minGuestCount}
      onBack={() => navigate(`/games/${checkoutData.game.id}`)}
      onConfirmBooking={handleConfirm}
      onGuestCountChange={(nextGuestCount) => {
        setGuestCount(nextGuestCount)
        resetStripeCheckout()
      }}
      onSelectPaymentMethod={(paymentMethodId) => {
        setSelectedPaymentMethodId(paymentMethodId)
        resetStripeCheckout()
      }}
      onSetAgreed={setAgreed}
      paymentMethod={checkout.paymentMethod}
      paymentMethods={checkout.paymentMethods}
      platformFee={checkout.platformFee}
      price={checkout.price}
      primaryImage={checkout.primaryImage}
      projectedGuestCount={checkout.projectedGuestCount}
      selectedPaymentMethodId={selectedPaymentMethodId}
      submitError={submitError}
      stripeStatusMessage={stripeStatusMessage}
      stripeUnavailable={stripeUnavailable}
      title={checkout.title}
      total={checkout.total}
    />
  )

  return renderLayout()
}

function getConfirmLabel({
  agreed,
  fallbackLabel,
  isStripeCheckout,
  isStripeReady,
  isSubmitting,
  usesSavedPaymentMethod,
}) {
  if (!isStripeCheckout) {
    return fallbackLabel
  }

  if (isSubmitting) {
    return 'Confirming...'
  }

  if (!agreed) {
    return 'Accept Terms to Continue'
  }

  if (!isStripeReady) {
    return 'Payment Unavailable'
  }

  if (!usesSavedPaymentMethod) {
    return 'Add Card to Continue'
  }

  return 'Confirm & Pay'
}

export default GameCheckoutPage
