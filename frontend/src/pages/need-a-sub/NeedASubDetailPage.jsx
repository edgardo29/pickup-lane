import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import {
  cancelNeedASubRequest,
  requestNeedASubSpot,
} from './needASubApi.js'
import NeedASubDetailContent from './NeedASubDetailContent.jsx'
import { MAX_WAITLIST_REQUESTS_PER_POST } from './needASubData.js'
import { countHeldSpots } from './needASubSelectors.js'
import { useNeedASubDetailData } from './useNeedASubDetailData.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubDetailPage() {
  const { postId } = useParams()
  const { appUser, currentUser } = useAuth()
  const [isActing, setIsActing] = useState(false)
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
  const canRequest = Boolean(
    currentUser &&
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

  return (
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-detail-shell">
        <div className="need-sub-manage-top">
          <Link className="need-sub-back-link" to="/need-a-sub">← Back</Link>
        </div>

        {error && (
          <div className="need-sub-alert need-sub-alert--error">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="need-sub-empty">Loading post...</div>
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
    </AppPageShell>
  )
}

export default NeedASubDetailPage
