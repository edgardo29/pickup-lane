import { JoinActionStack } from './GameDetailsJoinActions.jsx'
import { SidebarQuickFacts } from './GameDetailsQuickFacts.jsx'
import { SidebarAboutSection, SidebarQuestionsSection } from './GameDetailsSidebarInfo.jsx'

export function JoinCard({
  aboutText,
  cancelGameDisabled = false,
  editGameUrl,
  editGameDisabled = false,
  facts,
  gameToneLabel,
  hostPaymentMethods = [],
  hostGuestCount,
  hostGuestMax,
  isAddingHostGuest,
  isCancellingGame,
  isUpdatingHostGuests,
  joinDisabled,
  joinLabel,
  joinMessage,
  joinNotice,
  leaveLabel,
  manageHostGuestsDisabled = false,
  onJoin,
  onCancelGame,
  onLeave,
  onManageHostGuests,
  onShare,
  price,
  returnPath,
  shareCopied,
  shareDisabled = false,
}) {
  return (
    <div className="details-booking-card">
      <div className="details-booking-card__price">
        <strong>{price}</strong>
        <span>per player</span>
      </div>

      <JoinActionStack
        cancelGameDisabled={cancelGameDisabled}
        editGameDisabled={editGameDisabled}
        editGameUrl={editGameUrl}
        hostGuestCount={hostGuestCount}
        hostGuestMax={hostGuestMax}
        isAddingHostGuest={isAddingHostGuest}
        isCancellingGame={isCancellingGame}
        isUpdatingHostGuests={isUpdatingHostGuests}
        joinDisabled={joinDisabled}
        joinLabel={joinLabel}
        joinMessage={joinMessage}
        joinNotice={joinNotice}
        leaveLabel={leaveLabel}
        manageHostGuestsDisabled={manageHostGuestsDisabled}
        onCancelGame={onCancelGame}
        onJoin={onJoin}
        onLeave={onLeave}
        onManageHostGuests={onManageHostGuests}
        onShare={onShare}
        returnPath={returnPath}
        shareCopied={shareCopied}
        shareDisabled={shareDisabled}
      />

      <SidebarQuickFacts facts={facts} gameToneLabel={gameToneLabel} />
      <SidebarAboutSection aboutText={aboutText} hostPaymentMethods={hostPaymentMethods} />
      <SidebarQuestionsSection />
    </div>
  )
}
