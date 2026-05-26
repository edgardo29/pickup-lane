import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import {
  ArrowLeftIcon,
  PlusCircleIcon,
} from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import NeedASubForm from './NeedASubForm.jsx'
import NeedASubPostList, { NeedASubState } from './NeedASubPostList.jsx'
import { POST_TABS } from './needASubData.js'
import { useNeedASubCreateForm } from './useNeedASubCreateForm.js'
import { useNeedASubPostsData } from './useNeedASubPostsData.js'
import '../../styles/need-a-sub/NeedASub.css'

function NeedASubPage() {
  const { currentUser, isLoading: isAuthLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [notice, setNotice] = useState('')
  const [activePanel, setActivePanel] = useState('browse')
  const [postView, setPostView] = useState('all')
  const {
    error,
    isLoading,
    myPosts,
    posts,
    refreshNeedASub,
    setError,
  } = useNeedASubPostsData({
    currentUser,
    isAuthLoading,
  })
  const {
    addPosition,
    clearCreateFeedback,
    form,
    formError,
    isCreating,
    removePosition,
    submitPost,
    totalSpotsNeeded,
    updateField,
    updateGamePlayerGroup,
    updatePosition,
  } = useNeedASubCreateForm({
    currentUser,
    navigate,
    refreshNeedASub,
    setActivePanel,
    setError,
    setNotice,
    setPostView,
  })

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
  }, [location.pathname, location.state, navigate])

  const visiblePosts = postView === 'mine' ? myPosts : posts

  function showBrowsePanel() {
    clearCreateFeedback()
    setActivePanel('browse')
  }

  function showCreatePanel() {
    clearCreateFeedback()
    setActivePanel('create')
  }

  function switchPostView(nextView) {
    setPostView(nextView)
    refreshNeedASub({ showLoading: true })
  }

  return (
    <AppPageShell
      className="need-sub-page"
      mainClassName={`need-sub-shell ${activePanel === 'create' ? 'need-sub-shell--form' : ''}`}
    >
      <AppPageHeader
        title={activePanel === 'create' ? 'Post Details' : 'Need a Sub'}
        subtitle={
          activePanel === 'create'
            ? 'Post a substitute request for an outside game.'
            : 'Post or request substitute spots for outside games.'
        }
        actions={
          activePanel === 'create' ? (
            <button
              className="need-sub-header-action need-sub-header-action--secondary"
              type="button"
              onClick={showBrowsePanel}
            >
              <ArrowLeftIcon />
              Back to Posts
            </button>
          ) : null
        }
      />

      {activePanel === 'browse' && (
        <div className="need-sub-browse-controls">
          <AppTabs
            ariaLabel="Need a Sub posts"
            items={POST_TABS}
            onChange={switchPostView}
            value={postView}
          />
          <button
            className="need-sub-header-action need-sub-header-action--primary"
            type="button"
            onClick={showCreatePanel}
          >
            <PlusCircleIcon />
            Create Post
          </button>
        </div>
      )}

      {(notice || error) && (
        <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
          {error || notice}
        </div>
      )}

      {activePanel === 'create' ? (
        currentUser ? (
          <section className="need-sub-panel need-sub-create-panel">
            <NeedASubForm
              formError={formError}
              form={form}
              isSaving={isCreating}
              totalSpotsNeeded={totalSpotsNeeded}
              onAddPosition={addPosition}
              onRemovePosition={removePosition}
              onSubmit={submitPost}
              onUpdateField={updateField}
              onUpdateGamePlayerGroup={updateGamePlayerGroup}
              onUpdatePosition={updatePosition}
            />
          </section>
        ) : (
          <NeedASubState
            title="Sign in to create a post"
            message="You can browse open sub needs now. Create an account when your team needs players."
            action={<Link to="/sign-in" state={{ from: '/need-a-sub' }}>Sign In</Link>}
          />
        )
      ) : (
        <NeedASubPostList
          isLoading={isLoading}
          isSignedIn={Boolean(currentUser)}
          onOpenPost={(post) => navigate(`/need-a-sub/posts/${post.id}`)}
          posts={visiblePosts}
          postView={postView}
        />
      )}
    </AppPageShell>
  )
}

export default NeedASubPage
