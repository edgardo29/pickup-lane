import { NeedASubDetailHero } from './NeedASubDetailHero.jsx'
import { NeedASubOwnerPanel } from './NeedASubOwnerPanel.jsx'
import { NeedASubRequestPanel } from './NeedASubRequestPanel.jsx'

function NeedASubDetailContent({
  activeRequest,
  canRequest,
  canSubmitRequest,
  currentUser,
  isActing,
  isOwner,
  isPostWaitlistFull,
  onCancelRequest,
  onRequestSpot,
  onSelectPosition,
  ownerRequests,
  post,
  requestNotice,
  selectedPositionId,
  selectedPositionNeedsWaitlist,
}) {
  return (
    <div className="need-sub-detail-grid">
      <NeedASubDetailHero post={post} />

      {isOwner ? (
        <NeedASubOwnerPanel postId={post.id} requests={ownerRequests} />
      ) : (
        <NeedASubRequestPanel
          activeRequest={activeRequest}
          canRequest={canRequest}
          canSubmitRequest={canSubmitRequest}
          currentUser={currentUser}
          isActing={isActing}
          isPostWaitlistFull={isPostWaitlistFull}
          onCancelRequest={onCancelRequest}
          onRequestSpot={onRequestSpot}
          onSelectPosition={onSelectPosition}
          post={post}
          requestNotice={requestNotice}
          selectedPositionId={selectedPositionId}
          selectedPositionNeedsWaitlist={selectedPositionNeedsWaitlist}
        />
      )}
    </div>
  )
}

export default NeedASubDetailContent
