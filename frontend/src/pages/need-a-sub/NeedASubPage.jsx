import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import { PlusCircleIcon } from '../../components/BrowseIcons.jsx'
import { EmailVerificationBlocker } from '../../features/email-verification/EmailVerificationBlocker.jsx'
import { useEmailVerification } from '../../features/email-verification/useEmailVerification.js'
import { useAuth } from '../../hooks/useAuth.js'
import { NeedASubCreateDiscardModal } from './NeedASubCreateDiscardModal.jsx'
import NeedASubCreateFlow from './NeedASubCreateFlow.jsx'
import NeedASubDateStrip from './NeedASubDateStrip.jsx'
import NeedASubPostList, { NeedASubState } from './NeedASubPostList.jsx'
import { NEED_A_SUB_TIME_ZONE, POST_TABS } from './needASubData.js'
import { useNeedASubCreateForm } from './useNeedASubCreateForm.js'
import { useNeedASubPostsData } from './useNeedASubPostsData.js'
import '../../styles/need-a-sub/NeedASub.css'

const NEED_SUB_DATE_STRIP_DAYS = 7
const NEED_SUB_MAX_DATE_PAGE_INDEX = 1

function NeedASubPage() {
  const { appUser, currentUser, isLoading: isAuthLoading, refreshCurrentUserVerification, sendCurrentUserVerificationEmail } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [notice, setNotice] = useState('')
  const [activePanel, setActivePanel] = useState(() => new URLSearchParams(location.search).get('panel') === 'create' ? 'create' : 'browse')
  const [selectedPostView, setPostView] = useState('all')
  const [todayKey, setTodayKey] = useState(() => getMarketDateKey(new Date()))
  const [datePageIndex, setDatePageIndex] = useState(0)
  const [selectedDateKey, setSelectedDateKey] = useState(todayKey)
  const [showCreateDiscardModal, setShowCreateDiscardModal] = useState(false)
  // A sign-in without a finished Pickup Lane account browses as a guest.
  const accountUser = appUser ? currentUser : null
  const isSignedIn = Boolean(accountUser)
  const postView = isSignedIn ? selectedPostView : 'all'
  const {
    error,
    hasLoadFailed,
    hasMorePosts,
    isLoading,
    isLoadingMore,
    loadMoreNeedASub,
    posts,
    retryNeedASub,
    setError,
  } = useNeedASubPostsData({
    currentUser: accountUser,
    isAuthLoading,
    onReturn: moveToCurrentDate,
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
    preserveForVerification,
    resetCreateForm,
    submitPost,
    totalSpotsNeeded,
    updateField,
    updateGamePlayerGroup,
    updatePosition,
  } = useNeedASubCreateForm({
    currentUser: accountUser,
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
      navigate(`${location.pathname}${location.search}`, { replace: true })
    }, 0)

    return () => window.clearTimeout(timerId)
  }, [location.pathname, location.search, location.state, navigate])

  const verification = useEmailVerification({
    appUser, enabled: activePanel === 'create', destination: '/need-a-sub?panel=create',
    refreshCurrentUserVerification, sendCurrentUserVerificationEmail,
  })

  const maxDatePageIndex = NEED_SUB_MAX_DATE_PAGE_INDEX
  const visibleDateOptions = useMemo(
    () => buildDateOptions(todayKey, datePageIndex),
    [todayKey, datePageIndex],
  )

  // After midnight in Chicago the strip starts at the new today; a selected
  // date that has passed moves to today.
  function moveToCurrentDate() {
    const nextTodayKey = getMarketDateKey(new Date())

    if (nextTodayKey === todayKey) {
      return
    }

    const nextSelectedDateKey = selectedDateKey < nextTodayKey ? nextTodayKey : selectedDateKey
    setTodayKey(nextTodayKey)
    setSelectedDateKey(nextSelectedDateKey)
    setDatePageIndex(Math.min(
      Math.floor(countDaysBetween(nextTodayKey, nextSelectedDateKey) / NEED_SUB_DATE_STRIP_DAYS),
      NEED_SUB_MAX_DATE_PAGE_INDEX,
    ))
  }

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

  function openPost(post) {
    const postPath = `/need-a-sub/posts/${post.id}`

    if (isSignedIn) {
      navigate(postPath)
      return
    }

    // Full post details need an account; come back to this post afterward.
    navigate('/sign-in', { state: { backTo: '/need-a-sub', from: postPath } })
  }

  function moveDatePage(nextPageIndex) {
    const normalizedPageIndex = Math.min(
      Math.max(nextPageIndex, 0),
      maxDatePageIndex,
    )
    setDatePageIndex(normalizedPageIndex)
    setSelectedDateKey(buildDateOptions(todayKey, normalizedPageIndex)[0].key)
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

      {activePanel === 'browse' && (
        <>
          {isSignedIn && (
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
        <div
          className={`need-sub-alert ${error ? 'need-sub-alert--error' : ''}`}
          role={error ? 'alert' : 'status'}
        >
          {error || notice}
        </div>
      )}

      {activePanel === 'create' ? (
        isSignedIn ? (
          <section className="need-sub-panel need-sub-create-panel">
            {!appUser?.email_verified_at ? (
              <EmailVerificationBlocker
                cooldownSeconds={verification.verificationCooldownSeconds}
                error={verification.verificationError}
                notice={verification.verificationNotice}
                status={verification.verificationStatus}
                onSend={() => { preserveForVerification(); return verification.sendEmailVerificationLink() }}
              />
            ) : (
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
            )}
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
          hasLoadFailed={hasLoadFailed}
          isLoading={isLoading}
          isLoadingMore={isLoadingMore}
          hasMorePosts={hasMorePosts}
          onLoadMore={loadMoreNeedASub}
          onOpenPost={openPost}
          onRetry={retryNeedASub}
          posts={posts}
          postView={postView}
        />
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

// Date keys are Chicago calendar dates (YYYY-MM-DD), the dates posts are filed
// under. Calendar arithmetic runs in UTC so daylight saving cannot skip a day.
function buildDateOptions(todayKey, pageIndex) {
  const firstDayOffset = pageIndex * NEED_SUB_DATE_STRIP_DAYS

  return Array.from({ length: NEED_SUB_DATE_STRIP_DAYS }, (_, index) => {
    const date = dateFromKey(todayKey)
    date.setUTCDate(date.getUTCDate() + firstDayOffset + index)
    const format = (options) => new Intl.DateTimeFormat('en-US', { ...options, timeZone: 'UTC' }).format(date)

    return {
      day: format({ day: 'numeric' }),
      key: date.toISOString().slice(0, 10),
      month: format({ month: 'short' }),
      weekday: format({ weekday: 'short' }),
    }
  })
}

function getMarketDateKey(now) {
  // en-CA writes dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', {
    day: '2-digit',
    month: '2-digit',
    timeZone: NEED_A_SUB_TIME_ZONE,
    year: 'numeric',
  }).format(now)
}

function dateFromKey(dateKey) {
  const [year, month, day] = dateKey.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day))
}

function countDaysBetween(startKey, endKey) {
  return Math.round((dateFromKey(endKey) - dateFromKey(startKey)) / 86_400_000)
}

export default NeedASubPage
