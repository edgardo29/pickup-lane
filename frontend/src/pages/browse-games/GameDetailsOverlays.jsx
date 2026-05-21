import { ChatPanel } from './GameDetailsChat.jsx'
import { PlayersListModal } from './GameDetailsPlayers.jsx'
import { CancelGameModal } from './CancelGameModal.jsx'
import { HostGuestModal } from './HostGuestModal.jsx'
import { LeaveGameModal } from './LeaveGameModal.jsx'

function GameDetailsOverlays({
  activePlayerTab,
  bookingGuestAddSlots,
  canAddBookingGuests,
  chatDraft,
  chatError,
  chatMessageMaxLength,
  chatMessages,
  chatSenderNames,
  currentGuestCount,
  currentParticipant,
  currentUser,
  currentUserName,
  game,
  hostGuestAddSlots,
  hostGuestMax,
  isAddingHostGuest,
  isCancelGameModalOpen,
  isCancellingGame,
  isChatOpen,
  isHostGuestModalOpen,
  isLeaveModalOpen,
  isLeaving,
  isPlayerListOpen,
  isSendingChatMessage,
  isUpdatingGuests,
  onAddBookingGuests,
  onCancelGame,
  onChangeChatDraft,
  onCloseCancelGameModal,
  onCloseChat,
  onCloseHostGuestModal,
  onCloseLeaveModal,
  onClosePlayerList,
  onLeaveGame,
  onRemoveGuests,
  onSaveHostGuestCount,
  onSelectPlayerTab,
  onSendChatMessage,
  participantSummary,
  playerGuestMax,
}) {
  return (
    <>
      {isPlayerListOpen && (
        <PlayersListModal
          onClose={onClosePlayerList}
          activeTab={activePlayerTab}
          onSelectTab={onSelectPlayerTab}
          participantSummary={participantSummary}
        />
      )}

      {isChatOpen && (
        <ChatPanel
          currentUserId={currentUser?.id || ''}
          currentUserName={currentUserName}
          draft={chatDraft}
          error={chatError}
          isSending={isSendingChatMessage}
          maxLength={chatMessageMaxLength}
          messages={chatMessages}
          onChangeDraft={onChangeChatDraft}
          onClose={onCloseChat}
          onSend={onSendChatMessage}
          senderNames={chatSenderNames}
        />
      )}

      {isHostGuestModalOpen && (
        <HostGuestModal
          guestCount={currentGuestCount}
          guestMax={hostGuestMax}
          addableCount={hostGuestAddSlots}
          isAdding={isAddingHostGuest}
          isRemoving={isUpdatingGuests}
          onClose={onCloseHostGuestModal}
          onSave={onSaveHostGuestCount}
        />
      )}

      {isCancelGameModalOpen && (
        <CancelGameModal
          gameType={game.game_type}
          isCancelling={isCancellingGame}
          onClose={onCloseCancelGameModal}
          onConfirm={onCancelGame}
        />
      )}

      {isLeaveModalOpen && (
        <LeaveGameModal
          addableGuestCount={bookingGuestAddSlots}
          canAddGuests={canAddBookingGuests}
          isLeaving={isLeaving}
          isUpdatingGuests={isUpdatingGuests}
          isWaitlisted={currentParticipant?.participant_status === 'waitlisted'}
          guestCount={currentGuestCount}
          guestMax={playerGuestMax}
          onClose={onCloseLeaveModal}
          onAddGuests={onAddBookingGuests}
          onConfirm={onLeaveGame}
          onRemoveGuests={onRemoveGuests}
        />
      )}
    </>
  )
}

export default GameDetailsOverlays
