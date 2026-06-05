import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AppPageHeader, AppPageShell } from '../../components/app/index.js'
import { useAuth } from '../../hooks/useAuth.js'
import { getNeedASubPost } from './needASubApi.js'
import NeedASubCreateFlow from './NeedASubCreateFlow.jsx'
import { NeedASubEditDiscardModal } from './NeedASubEditDiscardModal.jsx'
import { NeedASubManageSkeleton } from './NeedASubSkeleton.jsx'
import { useNeedASubEditForm } from './useNeedASubEditForm.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubEditPage() {
  const { postId } = useParams()
  const navigate = useNavigate()
  const { appUser, currentUser, isLoading: isAuthLoading } = useAuth()
  const [post, setPost] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const detailPath = `/need-a-sub/posts/${postId}`
  const isOwner = Boolean(appUser?.id && post?.owner_user_id === appUser.id)
  const canEditPost = Boolean(
    post &&
    ['active', 'filled'].includes(post.post_status) &&
    new Date(post.starts_at) > new Date(),
  )

  useEffect(() => {
    let ignore = false

    async function loadPost() {
      if (isAuthLoading) {
        return
      }

      if (!currentUser) {
        setIsLoading(false)
        setLoadError('Sign in to edit this post.')
        return
      }

      setIsLoading(true)
      setLoadError('')

      try {
        const postResponse = await getNeedASubPost(postId, currentUser)

        if (!ignore) {
          setPost(postResponse)
        }
      } catch (error) {
        if (!ignore) {
          setLoadError(error instanceof Error ? error.message : 'Unable to load post.')
        }
      } finally {
        if (!ignore) {
          setIsLoading(false)
        }
      }
    }

    loadPost()

    return () => {
      ignore = true
    }
  }, [currentUser, isAuthLoading, postId])

  return (
    <AppPageShell
      className="need-sub-page"
      mainClassName="need-sub-shell need-sub-shell--form need-sub-edit-shell"
    >
      {isLoading ? (
        <>
          <NeedASubEditHeader onBack={() => navigate(detailPath)} />
          <NeedASubManageSkeleton />
        </>
      ) : !post ? (
        <>
          <NeedASubEditHeader onBack={() => navigate(detailPath)} />
          {loadError && (
            <div className="need-sub-alert need-sub-alert--error">
              {loadError}
            </div>
          )}
          <div className="need-sub-empty">
            <strong>Post not found.</strong>
            <span>Go back to Need a Sub and choose another post.</span>
          </div>
        </>
      ) : !isOwner ? (
        <>
          <NeedASubEditHeader onBack={() => navigate(detailPath)} />
          <div className="need-sub-empty">
            <strong>You can only edit posts you created.</strong>
            <span>This post is visible from the All Posts tab.</span>
          </div>
        </>
      ) : !canEditPost ? (
        <>
          <NeedASubEditHeader onBack={() => navigate(detailPath)} />
          <div className="need-sub-empty">
            <strong>This post cannot be edited.</strong>
            <span>Only active or filled posts can be edited before the game starts.</span>
          </div>
        </>
      ) : (
        <NeedASubEditContent
          key={post.id}
          currentUser={currentUser}
          detailPath={detailPath}
          navigate={navigate}
          post={post}
        />
      )}
    </AppPageShell>
  )
}

function NeedASubEditContent({
  currentUser,
  detailPath,
  navigate,
  post,
}) {
  const [showDiscardModal, setShowDiscardModal] = useState(false)
  const {
    addEditPosition,
    editError,
    editForm,
    hasUnsavedChanges,
    isGamePlayerGroupOptionDisabled,
    isSavingEdit,
    removeEditPosition,
    submitEdit,
    totalEditSpotsNeeded,
    updateEditField,
    updateEditGamePlayerGroup,
    updateEditPosition,
  } = useNeedASubEditForm({
    currentUser,
    onSaved: () => {
      navigate(detailPath, {
        replace: true,
        state: { needASubNotice: 'Post updated.' },
      })
    },
    post,
  })

  function requestExit() {
    if (isSavingEdit) {
      return
    }

    if (hasUnsavedChanges) {
      setShowDiscardModal(true)
      return
    }

    navigate(detailPath)
  }

  function discardChanges() {
    setShowDiscardModal(false)
    navigate(detailPath)
  }

  return (
    <>
      <NeedASubEditHeader onBack={requestExit} />

      <section className="need-sub-panel need-sub-create-panel need-sub-edit-panel">
        <NeedASubCreateFlow
          form={editForm}
          formError={editError}
          isCreating={isSavingEdit}
          isDateLocked
          isGamePlayerGroupOptionDisabled={isGamePlayerGroupOptionDisabled}
          mode="edit"
          submitLabel="Save Changes"
          submittingLabel="Saving..."
          totalSpotsNeeded={totalEditSpotsNeeded}
          onAddPosition={addEditPosition}
          onCancel={requestExit}
          onRemovePosition={removeEditPosition}
          onSubmit={submitEdit}
          onUpdateField={updateEditField}
          onUpdateGamePlayerGroup={updateEditGamePlayerGroup}
          onUpdatePosition={updateEditPosition}
        />
      </section>

      {showDiscardModal && (
        <NeedASubEditDiscardModal
          onClose={() => setShowDiscardModal(false)}
          onDiscard={discardChanges}
        />
      )}
    </>
  )
}

function NeedASubEditHeader({ onBack }) {
  return (
    <AppPageHeader
      title="Edit Sub Post"
      subtitle="Update your outside game and substitute details."
      actions={(
        <button className="need-sub-back-link need-sub-edit-header-back" type="button" onClick={onBack}>
          ← Back
        </button>
      )}
    />
  )
}

export default NeedASubEditPage
