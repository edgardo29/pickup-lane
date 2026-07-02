import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import {
  PlusCircleIcon,
  UserIcon,
} from '../../components/BrowseIcons.jsx'
import { LockIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { NeedASubCreateDiscardModal } from './NeedASubCreateDiscardModal.jsx'
import NeedASubCreateFlow from './NeedASubCreateFlow.jsx'
import NeedASubDateStrip from './NeedASubDateStrip.jsx'
import NeedASubPostList, { NeedASubState } from './NeedASubPostList.jsx'
import { POST_TABS } from './needASubData.js'
import { useNeedASubCreateForm } from './useNeedASubCreateForm.js'
import { useNeedASubPostsData } from './useNeedASubPostsData.js'
import '../../styles/need-a-sub/NeedASub.css'

const NEED_SUB_DATE_STRIP_DAYS = 7
const NEED_SUB_MAX_DATE_PAGE_INDEX = 1

function NeedASubPage() {
  const { currentUser, isLoading: isAuthLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [notice, setNotice] = useState('')
  const [activePanel, setActivePanel] = useState('browse')
  const [postView, setPostView] = useState('all')
  const [datePageIndex, setDatePageIndex] = useState(0)
  const [selectedDateKey, setSelectedDateKey] = useState(() => getLocalDateKey(new Date()))
  const [showCreateDiscardModal, setShowCreateDiscardModal] = useState(false)
  const {
    error,
    hasMorePosts,
    isLoading,
    isLoadingMore,
    loadMoreNeedASub,
    posts,
    setError,
  } = useNeedASubPostsData({
    currentUser,
    isAuthLoading,
    postView,
    selectedDateKey,
  })
  const {
    addPosition,
    form,
    formError,
    hasCreateChanges,
    isCreating,
    checkDuplicateDate,
    clearCreateFeedback,
    removePosition,
    resetCreateForm,
    submitPost,
    totalSpotsNeeded,
    updateField,
    updateGamePlayerGroup,
    updatePosition,
  } = useNeedASubCreateForm({
    currentUser,
    navigate,
    setError,
    setNotice,
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

  const maxDatePageIndex = NEED_SUB_MAX_DATE_PAGE_INDEX
  const isGuestBrowse = activePanel === 'browse' && !isAuthLoading && !currentUser
  const visibleDateOptions = useMemo(
    () => buildDateOptions(datePageIndex),
    [datePageIndex],
  )

  function showBrowsePanel() {
    setShowCreateDiscardModal(false)
    resetCreateForm()
    setActivePanel('browse')
  }

  function showCreatePanel() {
    setShowCreateDiscardModal(false)
    resetCreateForm()
    setActivePanel('create')
  }

  function requestCreateCancel() {
    if (hasCreateChanges) {
      setShowCreateDiscardModal(true)
      return
    }

    showBrowsePanel()
  }

  function switchPostView(nextView) {
    setPostView(nextView)
  }

  function moveDatePage(nextPageIndex) {
    const normalizedPageIndex = Math.min(
      Math.max(nextPageIndex, 0),
      maxDatePageIndex,
    )
    setDatePageIndex(normalizedPageIndex)
    setSelectedDateKey(buildDateOptions(normalizedPageIndex)[0]?.key || selectedDateKey)
  }

  return (
    <AppPageShell
      className="need-sub-page"
      mainClassName={`need-sub-shell ${activePanel === 'create' ? 'need-sub-shell--form' : ''}`}
    >
      <AppPageHeader
        title={activePanel === 'create' ? 'Create Sub Post' : 'Need a Sub'}
        subtitle={
          activePanel === 'create'
            ? 'Post a substitute request for an outside game.'
            : 'Post or request substitute spots for outside games.'
        }
      />

      {activePanel === 'browse' && !isGuestBrowse && (
        <>
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

          <NeedASubDateStrip
            canGoNext={datePageIndex < maxDatePageIndex}
            canGoPrevious={datePageIndex > 0}
            dates={visibleDateOptions}
            onNext={() => moveDatePage(datePageIndex + 1)}
            onPrevious={() => moveDatePage(datePageIndex - 1)}
            onSelectDate={setSelectedDateKey}
            selectedDateKey={selectedDateKey}
          />
        </>
      )}

      {(notice || error) && (
        <div className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}>
          {error || notice}
        </div>
      )}

      {activePanel === 'create' ? (
        currentUser ? (
          <section className="need-sub-panel need-sub-create-panel">
            <NeedASubCreateFlow
              formError={formError}
              form={form}
              isCreating={isCreating}
              totalSpotsNeeded={totalSpotsNeeded}
              onCancel={requestCreateCancel}
              onAddPosition={addPosition}
              onCheckDuplicateDate={checkDuplicateDate}
              onClearFeedback={clearCreateFeedback}
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
        isGuestBrowse ? (
          <NeedASubGuestPreview />
        ) : (
          <NeedASubPostList
            isLoading={isLoading}
            isLoadingMore={isLoadingMore}
            isSignedIn={Boolean(currentUser)}
            hasMorePosts={hasMorePosts}
            onLoadMore={loadMoreNeedASub}
            onOpenPost={(post) => navigate(`/need-a-sub/posts/${post.id}`)}
            posts={posts}
            postView={postView}
          />
        )
      )}

      {showCreateDiscardModal && (
        <NeedASubCreateDiscardModal
          onClose={() => setShowCreateDiscardModal(false)}
          onDiscard={showBrowsePanel}
        />
      )}
    </AppPageShell>
  )
}

function NeedASubGuestPreview() {
  return (
    <section className="need-sub-guest-preview" aria-labelledby="need-sub-guest-preview-title">
      <div className="need-sub-guest-preview__inner">
        <div className="need-sub-guest-lock" aria-hidden="true">
          <LockIcon />
        </div>

        <p className="need-sub-guest-preview__eyebrow">Guest Preview</p>
        <h2 id="need-sub-guest-preview-title">How Need a Sub works</h2>
        <p className="need-sub-guest-preview__lede">
          Need a Sub helps hosts fill roster gaps fast. Hosts post the exact spots they need,
          and players can review the game details and request to fill in.
        </p>

        <div className="need-sub-guest-steps" aria-label="How Need a Sub works">
          <GuestPreviewStep
            icon={<PlusCircleIcon />}
            label="For hosts"
            title="Post who you need"
            copy="Hosts create a post for the players they need for a specific game."
          />
          <GuestPreviewStep
            icon={<UserIcon />}
            label="For players"
            title="Ask to fill in"
            copy="Players find games that need a substitute and request to join."
          />
        </div>

        <p className="need-sub-guest-note">
          Sign in or create an account to post who you need or request to fill in.
        </p>

        <div className="need-sub-guest-actions">
          <Link className="need-sub-guest-action need-sub-primary" to="/create-account" state={{ from: '/need-a-sub' }}>
            <PlusCircleIcon />
            Register
          </Link>
          <Link className="need-sub-guest-action need-sub-create-secondary" to="/sign-in" state={{ from: '/need-a-sub' }}>
            <LockIcon />
            Sign In
          </Link>
        </div>
      </div>
    </section>
  )
}

function GuestPreviewStep({ copy, icon, label, title }) {
  return (
    <article className="need-sub-guest-step">
      <div className="need-sub-guest-step__icon">{icon}</div>
      <span>{label}</span>
      <strong>{title}</strong>
      <p>{copy}</p>
    </article>
  )
}

function buildDateOptions(pageIndex) {
  const firstDate = startOfLocalDay(new Date())
  firstDate.setDate(firstDate.getDate() + (pageIndex * NEED_SUB_DATE_STRIP_DAYS))

  return Array.from({ length: NEED_SUB_DATE_STRIP_DAYS }, (_, index) => {
    const date = new Date(firstDate)
    date.setDate(firstDate.getDate() + index)

    return {
      day: new Intl.DateTimeFormat('en-US', { day: 'numeric' }).format(date),
      key: getLocalDateKey(date),
      month: new Intl.DateTimeFormat('en-US', { month: 'short' }).format(date),
      weekday: new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(date),
    }
  })
}

function getLocalDateKey(dateValue) {
  const date = startOfLocalDay(dateValue)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function startOfLocalDay(value) {
  const date = new Date(value)
  date.setHours(0, 0, 0, 0)
  return date
}

export default NeedASubPage
