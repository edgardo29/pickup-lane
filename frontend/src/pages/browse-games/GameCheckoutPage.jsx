import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import GameCheckoutLayout from './GameCheckoutLayout.jsx'
import { buildGameCheckoutViewModel } from './gameCheckoutViewModel.js'
import { useGameCheckoutActions } from './useGameCheckoutActions.js'
import { useGameCheckoutData } from './useGameCheckoutData.js'
import { useAuth } from '../../hooks/useAuth.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/browse-games/GameCheckoutPage.css'

function GameCheckoutPage() {
  const { gameId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { appUser, isLoading: isAuthLoading } = useAuth()
  const isAddGuestsCheckout = searchParams.get('mode') === 'add-guests'
  const requestedGuestCount = Number.parseInt(searchParams.get('guest_count') || '', 10)

  const [guestCount, setGuestCount] = useState(() => (
    isAddGuestsCheckout && Number.isFinite(requestedGuestCount)
      ? Math.max(requestedGuestCount, 1)
      : 0
  ))
  const [agreed, setAgreed] = useState(false)
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
    gameId,
    isAuthLoading,
    navigate,
  })
  const {
    confirmBooking,
    isSubmitting,
    resetSubmitError,
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
    venue: checkoutData.venue,
  })

  useEffect(() => {
    resetSubmitError()
  }, [appUser?.id, gameId, isAddGuestsCheckout, resetSubmitError])

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

  return (
    <GameCheckoutLayout
      address={checkout.address}
      agreed={agreed}
      appUser={appUser}
      confirmLabel={checkout.confirmLabel}
      effectiveGuestCount={checkout.effectiveGuestCount}
      existingParticipant={checkout.existingParticipant}
      game={checkoutData.game}
      isAddGuestsBlockedByParticipant={checkout.isAddGuestsBlockedByParticipant}
      isAddGuestsCheckout={isAddGuestsCheckout}
      isBlockedByCapacity={checkout.isBlockedByCapacity}
      isJoinWindowClosed={checkout.isJoinWindowClosed}
      isSubmitting={isSubmitting}
      isWaitlistCheckout={checkout.isWaitlistCheckout}
      maxGuests={checkout.maxGuests}
      maxSelectableGuests={checkout.maxSelectableGuests}
      minGuestCount={checkout.minGuestCount}
      onBack={() => navigate(`/games/${checkoutData.game.id}`)}
      onConfirmBooking={() =>
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
      onGuestCountChange={setGuestCount}
      onSetAgreed={setAgreed}
      paymentMethod={checkout.paymentMethod}
      platformFee={checkout.platformFee}
      price={checkout.price}
      primaryImage={checkout.primaryImage}
      projectedGuestCount={checkout.projectedGuestCount}
      submitError={submitError}
      title={checkout.title}
      total={checkout.total}
    />
  )
}

export default GameCheckoutPage
