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
  autoChargeConsent,
  canAddPaymentMethod,
  checkoutActionMessage,
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
  isPaidWaitlistCheckout,
  isSubmitting,
  isStripeCheckout,
  isStripeReady,
  isWaitlistCheckout,
  manageCardsPath,
  maxGuests,
  maxSelectableGuests,
  minGuestCount,
  onAddPaymentMethod,
  onAutoChargeConsentChange,
  onBack,
  onChangePaymentMethod,
  onRetryPaymentMethods,
  onConfirmBooking,
  onGuestCountChange,
  onOpenLegalPolicy,
  onSetAgreed,
  paymentMethod,
  paymentMethods,
  paymentMethodsError,
  platformFee,
  price,
  primaryImage,
  projectedGuestCount,
  quote,
  quoteError,
  quoteStatus,
  setupError,
  submitError,
  stripePaymentsDisabled,
  stripeStatusMessage,
  stripeUnavailable,
  title,
  total,
  usesCardSelection,
}) {
  const isPriceUnavailable = isStripeCheckout && quoteStatus !== 'success'
  const needsPaymentMethod =
    (isStripeCheckout && isStripeReady && !paymentMethod && quote?.payment_required === true) ||
    (isPaidWaitlistCheckout && !paymentMethod)
  const needsAutoChargeConsent = isPaidWaitlistCheckout && !autoChargeConsent
  const needsLoadedCards = isPaidWaitlistCheckout || (isStripeCheckout && quote?.payment_required)
  const confirmDisabled =
    !agreed ||
    stripePaymentsDisabled ||
    isPriceUnavailable ||
    needsPaymentMethod ||
    (needsLoadedCards && Boolean(paymentMethodsError)) ||
    needsAutoChargeConsent ||
    isSubmitting ||
    isBlockedByCapacity ||
    isJoinWindowClosed ||
    isAddGuestsBlockedByParticipant ||
    isExistingParticipantBlocked

  const actionMessage = !agreed
    ? 'Accept the terms to continue.'
    : stripePaymentsDisabled
      ? 'Official game payments are disabled for this demo.'
      : isPriceUnavailable
        ? quoteError || 'Loading your price...'
      : needsLoadedCards && paymentMethodsError
        ? paymentMethodsError
      : needsPaymentMethod
        ? 'Add a payment method to continue.'
        : needsAutoChargeConsent
          ? 'Agree to the possible later charge to join this waitlist.'
          : checkoutActionMessage

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
              autoChargeConsent={autoChargeConsent}
              canAddPaymentMethod={canAddPaymentMethod}
              isPaidWaitlistCheckout={isPaidWaitlistCheckout}
              isStripeCheckout={usesCardSelection}
              manageCardsPath={manageCardsPath}
              onAddPaymentMethod={onAddPaymentMethod}
              onAutoChargeConsentChange={onAutoChargeConsentChange}
              onChangePaymentMethod={onChangePaymentMethod}
              onRetryPaymentMethods={onRetryPaymentMethods}
              paymentMethod={paymentMethod}
              paymentMethods={paymentMethods}
              paymentMethodsError={paymentMethodsError}
              paymentRequired={quote ? quote.payment_required : true}
              setupError={setupError}
              stripePaymentsDisabled={stripePaymentsDisabled}
              stripeStatusMessage={stripeStatusMessage}
              stripeUnavailable={stripeUnavailable}
              waitlistChargeCents={total}
            />

            <GameCheckoutPolicyCard game={game} />

            <GameCheckoutAgreementCard
              agreed={agreed}
              onOpenPolicy={onOpenLegalPolicy}
              onSetAgreed={onSetAgreed}
            />

            <GameCheckoutErrors
              existingParticipant={existingParticipant}
              isAddGuestsBlockedByParticipant={isAddGuestsBlockedByParticipant}
              isAddGuestsCheckout={isAddGuestsCheckout}
              isExistingParticipantBlocked={isExistingParticipantBlocked}
              isJoinWindowClosed={isJoinWindowClosed}
              submitError={submitError}
            />

            <GameCheckoutMobileAction
              actionMessage={actionMessage}
              confirmDisabled={confirmDisabled}
              confirmLabel={confirmLabel}
              onConfirmBooking={onConfirmBooking}
            />
          </div>

          <GameCheckoutSummaryCard
            actionMessage={actionMessage}
            confirmDisabled={confirmDisabled}
            confirmLabel={confirmLabel}
            effectiveGuestCount={effectiveGuestCount}
            isAddGuestsCheckout={isAddGuestsCheckout}
            isWaitlistCheckout={isWaitlistCheckout}
            onConfirmBooking={onConfirmBooking}
            platformFee={platformFee}
            price={price}
            quote={isStripeCheckout || isWaitlistCheckout ? quote : null}
            total={total}
          />
        </div>
      </main>
    </div>
  )
}

export default GameCheckoutLayout
