import { NeedASubDetailHero } from './NeedASubDetailHero.jsx'
import { NeedASubNextSteps } from './NeedASubNextSteps.jsx'
import { NeedASubOwnerPanel } from './NeedASubOwnerPanel.jsx'
import { NeedASubPostDetails } from './NeedASubPostDetails.jsx'
import { NeedASubRequestPanel } from './NeedASubRequestPanel.jsx'

function NeedASubDetailContent({
  activeRequest,
  canRequest,
  canSubmitRequest,
  canSelectSpot,
  canCancelPost,
  canEditPost,
  canManageRequests,
  currentUser,
  isActing,
  isOwner,
  isPostWaitlistFull,
  onCancelRequest,
  onCancelPost,
  onManageRequests,
  onRequestSpot,
  onSelectPosition,
  ownerRequests,
  post,
  requestNotice,
  selectedPositionId,
  selectedPositionNeedsWaitlist,
}) {
  const actionPanel = isOwner ? (
    <NeedASubOwnerPanel
      canCancelPost={canCancelPost}
      canEditPost={canEditPost}
      canManageRequests={canManageRequests}
      post={post}
      postId={post.id}
      requests={ownerRequests}
      onCancelPost={onCancelPost}
      onManageRequests={onManageRequests}
    />
  ) : (
    <NeedASubRequestPanel
      activeRequest={activeRequest}
      canRequest={canRequest}
      canSubmitRequest={canSubmitRequest}
      canSelectSpot={canSelectSpot}
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
  )

  return (
    <div className={`need-sub-detail-page need-sub-detail-page--${isOwner ? 'owner' : 'request'}`}>
      <NeedASubDetailHero post={post} />

      <NeedASubPostDetails currentUser={currentUser} post={post} />

      <div className={`need-sub-detail-action-row need-sub-detail-action-row--${isOwner ? 'owner' : 'request'}`}>
        <aside className="need-sub-detail-action-panel">
          {actionPanel}
        </aside>
      </div>

      <NeedASubNextSteps role={isOwner ? 'owner' : 'requester'} />
    </div>
  )
}

export default NeedASubDetailContent
