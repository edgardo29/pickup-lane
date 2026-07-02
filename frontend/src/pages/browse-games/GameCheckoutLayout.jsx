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
  canAddPaymentMethod,
  confirmLabel,
  effectiveGuestCount,
  existingParticipant,
  game,
  isAddGuestsBlockedByParticipant,
  isAddGuestsCheckout,
  isBlockedByCapacity,
  isExistingParticipantBlocked,
  isGuestSelectionLocked,
  isJoinWindowClosed,
  isPaymentActionBlocked,
  isSubmitting,
  isStripeCheckout,
  isWaitlistCheckout,
  maxGuests,
  maxSelectableGuests,
  minGuestCount,
  onAddPaymentMethod,
  onBack,
  onChangePaymentMethod,
  onConfirmBooking,
  onGuestCountChange,
  onSetAgreed,
  paymentMethod,
  paymentMethods,
  platformFee,
  price,
  primaryImage,
  projectedGuestCount,
  setupError,
  submitError,
  stripeStatusMessage,
  stripeUnavailable,
  title,
  total,
}) {
  const confirmDisabled =
    !agreed ||
    isSubmitting ||
    isBlockedByCapacity ||
    isJoinWindowClosed ||
    isAddGuestsBlockedByParticipant ||
    isPaymentActionBlocked ||
    isExistingParticipantBlocked

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
              isGuestSelectionLocked={isGuestSelectionLocked}
              isWaitlistCheckout={isWaitlistCheckout}
              maxGuests={maxGuests}
              maxSelectableGuests={maxSelectableGuests}
              minGuestCount={minGuestCount}
              onGuestCountChange={onGuestCountChange}
              projectedGuestCount={projectedGuestCount}
            />

            <GameCheckoutPaymentCard
              canAddPaymentMethod={canAddPaymentMethod}
              isStripeCheckout={isStripeCheckout}
              onAddPaymentMethod={onAddPaymentMethod}
              onChangePaymentMethod={onChangePaymentMethod}
              paymentMethod={paymentMethod}
              paymentMethods={paymentMethods}
              setupError={setupError}
              stripeStatusMessage={stripeStatusMessage}
              stripeUnavailable={stripeUnavailable}
            />

            <GameCheckoutPolicyCard gameId={game.id} />

            <GameCheckoutAgreementCard agreed={agreed} onSetAgreed={onSetAgreed} />

            <GameCheckoutErrors
              existingParticipant={existingParticipant}
              isAddGuestsBlockedByParticipant={isAddGuestsBlockedByParticipant}
              isAddGuestsCheckout={isAddGuestsCheckout}
              isExistingParticipantBlocked={isExistingParticipantBlocked}
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
