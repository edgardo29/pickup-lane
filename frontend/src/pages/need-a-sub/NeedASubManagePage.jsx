import { useEffect } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import NeedASubManageReview from './NeedASubManageReview.jsx'
import { NeedASubManageSkeleton } from './NeedASubSkeleton.jsx'
import { useNeedASubManageActions } from './useNeedASubManageActions.js'
import { useNeedASubManageData } from './useNeedASubManageData.js'
import { useNeedASubRequestGroups } from './useNeedASubRequestGroups.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubManagePage() {
  const { postId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { appUser, currentUser } = useAuth()
  const {
    error,
    isLoading,
    loadManageView,
    notice,
    post,
    requests,
    setError,
    setNotice,
  } = useNeedASubManageData({
    appUser,
    currentUser,
    postId,
  })

  const {
    activeRequestStatus,
    requestGroups,
    selectedGroup,
    setActiveRequestStatus,
    setSelectedPositionId,
    setWaitlistModalGroup,
    waitlistModalGroup,
  } = useNeedASubRequestGroups({ post, requests })
  const {
    cancelPost,
    handleAcceptRequest,
    handleDeclineRequest,
    handleRemoveRequest,
  } = useNeedASubManageActions({
    currentUser,
    loadManageView,
    navigate,
    post,
    setError,
    setNotice,
  })
  const canCancelPost = post?.post_status === 'active'
  const isOwner = Boolean(appUser?.id && post?.owner_user_id === appUser.id)

  useEffect(() => {
    const routedNotice = location.state?.needASubNotice
    if (!routedNotice) {
      return
    }

    const timerId = window.setTimeout(() => {
      setNotice(routedNotice)
      navigate(location.pathname, { replace: true })
    }, 0)

    return () => window.clearTimeout(timerId)
  }, [location.pathname, location.state, navigate, setNotice])

  return (
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-manage-shell">
        <div className="need-sub-manage-top">
          <Link className="need-sub-back-link" to={`/need-a-sub/posts/${postId}`}>← Back</Link>
        </div>

        {(notice || error) && (
          <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
            {error || notice}
          </div>
        )}

        {isLoading ? (
          <NeedASubManageSkeleton />
        ) : !post ? (
          <div className="need-sub-empty">
            <strong>Post not found.</strong>
            <span>Go back to Need a Sub and choose another post.</span>
          </div>
        ) : !isOwner ? (
          <div className="need-sub-empty">
            <strong>You can only manage posts you created.</strong>
            <span>This post is visible from the All Posts tab.</span>
          </div>
        ) : (
          <NeedASubManageReview
            activeRequestStatus={activeRequestStatus}
            canCancelPost={canCancelPost}
            onAcceptRequest={handleAcceptRequest}
            onBeginEdit={() => navigate(`/need-a-sub/posts/${postId}/edit`)}
            onCancelPost={cancelPost}
            onCloseWaitlistModal={() => setWaitlistModalGroup(null)}
            onDeclineRequest={handleDeclineRequest}
            onRemoveRequest={handleRemoveRequest}
            onSelectPosition={setSelectedPositionId}
            onStatusChange={setActiveRequestStatus}
            onViewWaitlist={() => setWaitlistModalGroup(selectedGroup)}
            post={post}
            requestGroups={requestGroups}
            selectedGroup={selectedGroup}
            waitlistModalGroup={waitlistModalGroup}
          />
        )}
    </AppPageShell>
  )
}

export default NeedASubManagePage
