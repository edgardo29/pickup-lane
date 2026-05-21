import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import { GameCheckoutAgreementCard } from './GameCheckoutAgreementCard.jsx'
import { GameCheckoutErrors } from './GameCheckoutErrors.jsx'
import { GameCheckoutGameCard } from './GameCheckoutGameCard.jsx'
import { GameCheckoutHeader } from './GameCheckoutHeader.jsx'
import { GameCheckoutMobileAction } from './GameCheckoutMobileAction.jsx'
import { GameCheckoutPaymentCard } from './GameCheckoutPaymentCard.jsx'
import { GameCheckoutPlayerCard } from './GameCheckoutPlayerCard.jsx'
import { GameCheckoutPolicyCard } from './GameCheckoutPolicyCard.jsx'
import { GameCheckoutSummaryCard } from './GameCheckoutSummaryCard.jsx'

function GameCheckoutLayout({
  address,
  agreed,
  appUser,
  confirmLabel,
  effectiveGuestCount,
  existingParticipant,
  game,
  isAddGuestsBlockedByParticipant,
  isAddGuestsCheckout,
  isBlockedByCapacity,
  isJoinWindowClosed,
  isSubmitting,
  isWaitlistCheckout,
  maxGuests,
  maxSelectableGuests,
  minGuestCount,
  onBack,
  onConfirmBooking,
  onGuestCountChange,
  onSetAgreed,
  paymentMethod,
  platformFee,
  price,
  primaryImage,
  projectedGuestCount,
  submitError,
  title,
  total,
}) {
  const confirmDisabled =
    !agreed ||
    isSubmitting ||
    isBlockedByCapacity ||
    isJoinWindowClosed ||
    isAddGuestsBlockedByParticipant ||
    (!isAddGuestsCheckout && Boolean(existingParticipant))

  return (
    <div className="checkout-page">
      <BrowseAppNav />

      <main className="checkout-shell">
        <GameCheckoutHeader
          isAddGuestsCheckout={isAddGuestsCheckout}
          isWaitlistCheckout={isWaitlistCheckout}
          onBack={onBack}
        />

        <GameCheckoutGameCard
          address={address}
          game={game}
          primaryImage={primaryImage}
          title={title}
        />

        <div className="checkout-layout">
          <div className="checkout-stack">
            <GameCheckoutPlayerCard
              appUser={appUser}
              effectiveGuestCount={effectiveGuestCount}
              isAddGuestsCheckout={isAddGuestsCheckout}
              isBlockedByCapacity={isBlockedByCapacity}
              isWaitlistCheckout={isWaitlistCheckout}
              maxGuests={maxGuests}
              maxSelectableGuests={maxSelectableGuests}
              minGuestCount={minGuestCount}
              onGuestCountChange={onGuestCountChange}
              projectedGuestCount={projectedGuestCount}
            />

            <GameCheckoutPaymentCard paymentMethod={paymentMethod} />

            <GameCheckoutPolicyCard gameId={game.id} />

            <GameCheckoutAgreementCard agreed={agreed} onSetAgreed={onSetAgreed} />

            <GameCheckoutErrors
              existingParticipant={existingParticipant}
              isAddGuestsBlockedByParticipant={isAddGuestsBlockedByParticipant}
              isAddGuestsCheckout={isAddGuestsCheckout}
              isJoinWindowClosed={isJoinWindowClosed}
              submitError={submitError}
            />

            <GameCheckoutMobileAction
              confirmDisabled={confirmDisabled}
              confirmLabel={confirmLabel}
              onConfirmBooking={onConfirmBooking}
            />
          </div>

          <GameCheckoutSummaryCard
            confirmDisabled={confirmDisabled}
            confirmLabel={confirmLabel}
            effectiveGuestCount={effectiveGuestCount}
            isAddGuestsCheckout={isAddGuestsCheckout}
            isWaitlistCheckout={isWaitlistCheckout}
            onConfirmBooking={onConfirmBooking}
            platformFee={platformFee}
            price={price}
            total={total}
          />
        </div>
      </main>
    </div>
  )
}

export default GameCheckoutLayout
