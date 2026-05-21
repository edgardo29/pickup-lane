import { NeedASubOpenSpotsPanel } from './NeedASubOpenSpotsPanel.jsx'
import { NeedASubPlayerPanel } from './NeedASubPlayerPanel.jsx'
import { NeedASubWaitlistModal } from './NeedASubWaitlistModal.jsx'

function NeedASubRequestReview({
  activeRequestStatus,
  onAcceptRequest,
  onCloseWaitlistModal,
  onDeclineRequest,
  onRemoveRequest,
  onSelectPosition,
  onStatusChange,
  onViewWaitlist,
  requestGroups,
  selectedGroup,
  waitlistModalGroup,
}) {
  return (
    <>
      <div className="need-sub-manage-focus-grid" id="requests">
        <NeedASubOpenSpotsPanel
          onSelectPosition={onSelectPosition}
          requestGroups={requestGroups}
          selectedGroup={selectedGroup}
        />

        {selectedGroup && (
          <NeedASubPlayerPanel
            activeStatus={activeRequestStatus}
            group={selectedGroup}
            onAccept={onAcceptRequest}
            onDecline={onDeclineRequest}
            onRemove={onRemoveRequest}
            onStatusChange={onStatusChange}
            onViewWaitlist={onViewWaitlist}
          />
        )}
      </div>

      {waitlistModalGroup && (
        <NeedASubWaitlistModal
          group={waitlistModalGroup}
          onClose={onCloseWaitlistModal}
        />
      )}
    </>
  )
}

export default NeedASubRequestReview
