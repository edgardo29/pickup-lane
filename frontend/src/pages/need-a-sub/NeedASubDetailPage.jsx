import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import {
  cancelNeedASubRequest,
  requestNeedASubSpot,
} from './needASubApi.js'
import { NeedASubCancelPostModal } from './NeedASubCancelPostModal.jsx'
import NeedASubDetailContent from './NeedASubDetailContent.jsx'
import { NeedASubManageRequestsModal } from './NeedASubManageRequestsModal.jsx'
import { MAX_WAITLIST_REQUESTS_PER_POST } from './needASubData.js'
import { countHeldSpots } from './needASubSelectors.js'
import { NeedASubDetailSkeleton } from './NeedASubSkeleton.jsx'
import { useNeedASubManageActions } from './useNeedASubManageActions.js'
import { useNeedASubDetailData } from './useNeedASubDetailData.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubDetailPage() {
  const { postId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { appUser, currentUser } = useAuth()
  const [isActing, setIsActing] = useState(false)
  const [isCancelPostModalOpen, setIsCancelPostModalOpen] = useState(false)
  const [isCancellingPost, setIsCancellingPost] = useState(false)
  const [isManageRequestsOpen, setIsManageRequestsOpen] = useState(false)
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [notice, setNotice] = useState('')
  const {
    error,
    isLoading,
    loadDetail,
    myRequests,
    ownerRequests,
    post,
    setError,
  } = useNeedASubDetailData({
    appUser,
    currentUser,
    postId,
  })

  const postRequests = useMemo(
    () => myRequests.filter((request) => request.sub_post_id === postId),
    [myRequests, postId],
  )
  const activeRequest = useMemo(
    () =>
      postRequests.find((request) =>
        ['pending', 'confirmed', 'sub_waitlist'].includes(request.request_status),
      ),
    [postRequests],
  )
  const isOwner = Boolean(appUser?.id && post?.owner_user_id === appUser.id)
  const isUpcomingPost = post?.starts_at
    ? new Date(post.starts_at) > new Date()
    : false
  const canUseOwnerActions = Boolean(
    isOwner &&
    ['active', 'filled'].includes(post?.post_status) &&
    isUpcomingPost,
  )
  const canCancelPost = canUseOwnerActions
  const canEditPost = canUseOwnerActions
  const canManageRequests = canUseOwnerActions
  const canRequest = Boolean(
    currentUser &&
    ['active', 'filled'].includes(post?.post_status) &&
    !isOwner &&
    !activeRequest,
  )
  const canSelectSpot = Boolean(
    ['active', 'filled'].includes(post?.post_status) &&
    !isOwner &&
    !activeRequest,
  )
  const effectiveSelectedPositionId = selectedPositionId || post?.positions?.[0]?.id || ''
  const selectedPosition = (post?.positions || [])
    .find((position) => position.id === effectiveSelectedPositionId)
  const selectedPositionNeedsWaitlist = selectedPosition
    ? countHeldSpots(selectedPosition) >= selectedPosition.spots_needed
    : false
  const isPostWaitlistFull = Number(post?.sub_waitlist_count || 0) >= MAX_WAITLIST_REQUESTS_PER_POST
  const canSubmitRequest = Boolean(
    canRequest &&
    selectedPosition &&
    (!selectedPositionNeedsWaitlist || !isPostWaitlistFull),
  )
  const requestNotice = notice && !isOwner
    ? notice
    : ''
  const ownerNotice = notice && isOwner
    ? notice
    : ''
  const {
    cancelPost,
    handleAcceptRequest,
    handleDeclineRequest,
    handleRemoveRequest,
  } = useNeedASubManageActions({
    currentUser,
    loadManageView: loadDetail,
    navigate,
    post,
    setError,
    setNotice,
  })

  useEffect(() => {
    const routedNotice = location.state?.needASubNotice
    if (!routedNotice) {
      return undefined
    }

    const timerId = window.setTimeout(() => {
      setNotice(routedNotice)
      navigate(location.pathname, { replace: true })
    }, 0)

    return () => window.clearTimeout(timerId)
  }, [location.pathname, location.state, navigate])

  async function runAction(action, successMessage) {
    setIsActing(true)
    setNotice('')
    setError('')

    try {
      await action()
      setNotice(successMessage)
      await loadDetail()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'Unable to update request.')
    } finally {
      setIsActing(false)
    }
  }

  function openManageRequests() {
    setNotice('')
    setError('')
    setIsManageRequestsOpen(true)
  }

  async function confirmCancelPost() {
    if (isCancellingPost) {
      return
    }

    setIsCancellingPost(true)

    try {
      await cancelPost()
    } finally {
      setIsCancellingPost(false)
    }
  }

  return (
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-detail-shell">
        <div className="need-sub-detail-top">
          <Link className="need-sub-back-link" to="/need-a-sub">← Back</Link>
        </div>

        {(error || ownerNotice) && (
          <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
            {error || ownerNotice}
          </div>
        )}

        {isLoading ? (
          <NeedASubDetailSkeleton />
        ) : !post ? (
          <div className="need-sub-empty">
            <strong>Post not found.</strong>
            <span>Go back to Need a Sub and choose another post.</span>
          </div>
        ) : (
          <NeedASubDetailContent
            activeRequest={activeRequest}
            canRequest={canRequest}
            canSubmitRequest={canSubmitRequest}
            canSelectSpot={canSelectSpot}
            canCancelPost={canCancelPost}
            canEditPost={canEditPost}
            canManageRequests={canManageRequests}
            currentUser={currentUser}
            isActing={isActing}
            isOwner={isOwner}
            isPostWaitlistFull={isPostWaitlistFull}
            onCancelRequest={() =>
              runAction(
                () => cancelNeedASubRequest(currentUser, activeRequest.id),
                activeRequest.request_status === 'sub_waitlist'
                  ? 'Left waitlist'
                  : 'Request canceled',
              )
            }
            onCancelPost={() => setIsCancelPostModalOpen(true)}
            onManageRequests={openManageRequests}
            onRequestSpot={() =>
              runAction(
                () => requestNeedASubSpot(currentUser, post.id, selectedPosition.id),
                selectedPositionNeedsWaitlist
                  ? 'Added to waitlist'
                  : 'Request sent',
              )
            }
            onSelectPosition={setSelectedPositionId}
            ownerRequests={ownerRequests}
            post={post}
            requestNotice={requestNotice}
            selectedPositionId={effectiveSelectedPositionId}
            selectedPositionNeedsWaitlist={selectedPositionNeedsWaitlist}
          />
        )}
        {isManageRequestsOpen && post && (
          <NeedASubManageRequestsModal
            error={error}
            notice={ownerNotice}
            onAcceptRequest={handleAcceptRequest}
            onClose={() => setIsManageRequestsOpen(false)}
            onDeclineRequest={handleDeclineRequest}
            onRemoveRequest={handleRemoveRequest}
            post={post}
            requests={ownerRequests}
          />
        )}
        {isCancelPostModalOpen && (
          <NeedASubCancelPostModal
            isCancelling={isCancellingPost}
            onClose={() => setIsCancelPostModalOpen(false)}
            onConfirm={confirmCancelPost}
          />
        )}
    </AppPageShell>
  )
}

export default NeedASubDetailPage
