import { JoinActionStack } from './GameDetailsJoinActions.jsx'
import { SidebarQuestionsSection } from './GameDetailsSidebarInfo.jsx'
import { PlayersIcon } from '../../components/GameFactIcons.jsx'

export function JoinCard({
  cancelGameDisabled = false,
  editGameUrl,
  editGameDisabled = false,
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

      {onManageHostGuests && hostGuestMax > 0 && (
        <section
          className="details-sidebar-section details-host-guest-summary"
          aria-label={`${hostGuestCount} of ${hostGuestMax} host guests added`}
        >
          <h2 className="details-section-heading">
            <span className="details-section-icon">
              <PlayersIcon />
            </span>
            Host Guests
          </h2>
          <p>
            <strong>{hostGuestCount}/{hostGuestMax}</strong> added
          </p>
        </section>
      )}

      <SidebarQuestionsSection />
    </div>
  )
}
