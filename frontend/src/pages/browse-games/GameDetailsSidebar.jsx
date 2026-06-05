import { JoinCard } from './GameDetailsJoinCard.jsx'

export function GameDetailsSidebar({
  canCancelGame,
  canEditGame,
  canShowCancelGame,
  canShowEditGame,
  currentGuestCount,
  currentParticipant,
  game,
  guestJoinMessage,
  hostGuestMax,
  isAddingHostGuest,
  isCancelledGame,
  isCancellingGame,
  isHost,
  isJoinDisabled,
  isJoinWindowClosed,
  isUpdatingGuests,
  joinLabel,
  joinNotice,
  onJoin,
  onOpenCancelGameModal,
  onOpenHostGuestModal,
  onOpenLeaveModal,
  onShare,
  price,
  shareCopied,
}) {
  return (
    <aside className="details-sidebar" aria-label="Join game">
      <JoinCard
        joinMessage={guestJoinMessage}
        joinNotice={joinNotice}
        joinLabel={joinLabel}
        joinDisabled={isJoinDisabled}
        leaveLabel={
          currentParticipant?.participant_status === 'waitlisted'
            ? 'Leave Waitlist'
            : 'Edit Attendance'
        }
        onJoin={onJoin}
        onLeave={
          currentParticipant && !isHost && !isJoinWindowClosed
            ? onOpenLeaveModal
            : null
        }
        onShare={onShare}
        shareDisabled={isCancelledGame}
        onCancelGame={canShowCancelGame ? onOpenCancelGameModal : null}
        cancelGameDisabled={!canCancelGame}
        price={price}
        returnPath={`/games/${game.id}`}
        shareCopied={shareCopied}
        editGameUrl={canShowEditGame ? `/games/${game.id}/edit` : ''}
        editGameDisabled={!canEditGame}
        hostGuestCount={isHost ? currentGuestCount : 0}
        hostGuestMax={hostGuestMax}
        isAddingHostGuest={isAddingHostGuest}
        isUpdatingHostGuests={isUpdatingGuests}
        isCancellingGame={isCancellingGame}
        onManageHostGuests={isHost ? onOpenHostGuestModal : null}
        manageHostGuestsDisabled={isCancelledGame || isJoinWindowClosed}
      />
    </aside>
  )
}
