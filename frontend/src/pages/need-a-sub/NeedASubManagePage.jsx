import { Link, useNavigate, useParams } from 'react-router-dom'
import { AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import NeedASubForm from './NeedASubForm.jsx'
import NeedASubManageReview from './NeedASubManageReview.jsx'
import { useNeedASubEditForm } from './useNeedASubEditForm.js'
import { useNeedASubManageActions } from './useNeedASubManageActions.js'
import { useNeedASubManageData } from './useNeedASubManageData.js'
import { useNeedASubRequestGroups } from './useNeedASubRequestGroups.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubManagePage() {
  const { postId } = useParams()
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
    setPost,
  } = useNeedASubManageData({
    appUser,
    currentUser,
    postId,
  })

  const {
    addEditPosition,
    beginEdit,
    cancelEdit,
    editError,
    editForm,
    isEditing,
    isSavingEdit,
    removeEditPosition,
    submitEdit,
    totalEditSpotsNeeded,
    updateEditField,
    updateEditGamePlayerGroup,
    updateEditPosition,
  } = useNeedASubEditForm({
    currentUser,
    loadManageView,
    post,
    setError,
    setNotice,
    setPost,
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
  const canCancelPost = post && ['active', 'filled'].includes(post.post_status)
  const isOwner = Boolean(appUser?.id && post?.owner_user_id === appUser.id)

  return (
    <AppPageShell className="need-sub-page" mainClassName="need-sub-shell need-sub-manage-shell">
        <div className="need-sub-manage-top">
          {isEditing ? (
            <button className="need-sub-back-link" type="button" onClick={cancelEdit}>
              ← Back
            </button>
          ) : (
            <Link className="need-sub-back-link" to={`/need-a-sub/posts/${postId}`}>← Back</Link>
          )}
        </div>

        {(notice || error) && (
          <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
            {error || notice}
          </div>
        )}

        {isLoading ? (
          <div className="need-sub-empty">Loading post...</div>
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
          isEditing && editForm ? (
            <NeedASubForm
              form={editForm}
              formError={editError}
              isDateLocked
              isSaving={isSavingEdit}
              onAddPosition={addEditPosition}
              onCancel={cancelEdit}
              onRemovePosition={removeEditPosition}
              onSubmit={submitEdit}
              onUpdateField={updateEditField}
              onUpdateGamePlayerGroup={updateEditGamePlayerGroup}
              onUpdatePosition={updateEditPosition}
              submitLabel="Save"
              title="Edit Post"
              totalSpotsNeeded={totalEditSpotsNeeded}
            />
          ) : (
            <NeedASubManageReview
              activeRequestStatus={activeRequestStatus}
              canCancelPost={canCancelPost}
              onAcceptRequest={handleAcceptRequest}
              onBeginEdit={beginEdit}
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
          )
        )}
    </AppPageShell>
  )
}

export default NeedASubManagePage
