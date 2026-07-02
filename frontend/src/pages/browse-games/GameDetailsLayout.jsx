import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import { GameDetailsMainColumn } from './GameDetailsMainColumn.jsx'
import GameDetailsMobileJoinBar from './GameDetailsMobileJoinBar.jsx'
import GameDetailsOverlays from './GameDetailsOverlays.jsx'
import { GameDetailsSidebar } from './GameDetailsSidebar.jsx'

function GameDetailsLayout(props) {
  return (
    <div className="details-page">
      <BrowseAppNav />

      <main className="details-shell">
        <section className="details-layout">
          <GameDetailsMainColumn {...props} />
          <GameDetailsSidebar {...props} />
        </section>
      </main>

      <GameDetailsMobileJoinBar
        currentParticipant={props.currentParticipant}
        gameId={props.game.id}
        guestJoinMessage={props.guestJoinMessage}
        isCancelledGame={props.isCancelledGame}
        isClosedJoinStatus={props.isClosedJoinStatus}
        isHost={props.isHost}
        isJoinDisabled={props.isJoinDisabled}
        joinLabel={props.joinLabel}
        joinNotice={props.joinNotice}
        onJoin={props.onJoin}
        price={props.price}
      />

      <GameDetailsOverlays
        activePlayerTab={props.activePlayerTab}
        bookingGuestAddSlots={props.bookingGuestAddSlots}
        canAddBookingGuests={props.canAddBookingGuests}
        chatDraft={props.chatDraft}
        chatError={props.chatError}
        chatMessageMaxLength={props.chatMessageMaxLength}
        chatMessages={props.chatMessages}
        chatSenderNames={props.chatSenderNames}
        currentGuestCount={props.currentGuestCount}
        currentParticipant={props.currentParticipant}
        currentUser={props.currentUser}
        currentUserName={props.currentUserName}
        game={props.game}
        hostGuestAddSlots={props.hostGuestAddSlots}
        hostGuestMax={props.hostGuestMax}
        isAddingHostGuest={props.isAddingHostGuest}
        isCancelGameModalOpen={props.isCancelGameModalOpen}
        isCancellingGame={props.isCancellingGame}
        isChatOpen={props.isChatOpen}
        isHostGuestModalOpen={props.isHostGuestModalOpen}
        isLeaveModalOpen={props.isLeaveModalOpen}
        isLeaving={props.isLeaving}
        isPlayerListOpen={props.isPlayerListOpen}
        isSendingChatMessage={props.isSendingChatMessage}
        isUpdatingGuests={props.isUpdatingGuests}
        onAddBookingGuests={props.onAddBookingGuests}
        onCancelGame={props.onCancelGame}
        onChangeChatDraft={props.onChangeChatDraft}
        onCloseCancelGameModal={props.onCloseCancelGameModal}
        onCloseChat={props.onCloseChat}
        onCloseHostGuestModal={props.onCloseHostGuestModal}
        onCloseLeaveModal={props.onCloseLeaveModal}
        onClosePlayerList={props.onClosePlayerList}
        onLeaveGame={props.onLeaveGame}
        onRemoveGuests={props.onRemoveGuests}
        onSaveHostGuestCount={props.onSaveHostGuestCount}
        onSelectPlayerTab={props.onSelectPlayerTab}
        onSendChatMessage={props.onSendChatMessage}
        participantSummary={props.participantSummary}
        playerGuestMax={props.playerGuestMax}
      />
    </div>
  )
}

export default GameDetailsLayout
