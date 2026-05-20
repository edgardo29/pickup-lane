import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AppPageHeader, AppPageShell, AppTabs } from '../../components/app/index.js'
import {
  ArrowLeftIcon,
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  PlusCircleIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import NeedASubForm from './NeedASubForm.jsx'
import {
  createNeedASubPost,
  listMyNeedASubPosts,
  listNeedASubPosts,
} from './needASubApi.js'
import { POST_TABS, buildInitialNeedASubForm, getDefaultPositions, getNextPosition } from './needASubData.js'
import { buildNeedASubPayload } from './needASubPayloads.js'
import { countHeldSpots } from './needASubSelectors.js'
import { validateNeedASubForm } from './needASubValidation.js'
import {
  buildPostSubtitle,
  formatDateWithYear,
  formatStatus,
  formatTimeRangeOnly,
} from './needASubFormatters.js'
import '../../styles/need-a-sub.css'

function NeedASubPage() {
  const { currentUser, isLoading: isAuthLoading } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [posts, setPosts] = useState([])
  const [myPosts, setMyPosts] = useState([])
  const [form, setForm] = useState(() => buildInitialNeedASubForm())
  const [isCreating, setIsCreating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [activePanel, setActivePanel] = useState('browse')
  const [postView, setPostView] = useState('all')

  useEffect(() => {
    const routedNotice = location.state?.needASubNotice
    if (!routedNotice) {
      return
    }

    setNotice(routedNotice)
    navigate(location.pathname, { replace: true })
  }, [location.pathname, location.state, navigate])

  const refreshNeedASub = useCallback(async ({ showLoading = false } = {}) => {
    if (showLoading) {
      setIsLoading(true)
    }
    setError('')

    try {
      const [postsResponse, myPostsResponse] = await Promise.all([
        listNeedASubPosts(),
        currentUser ? listMyNeedASubPosts(currentUser).catch(() => []) : Promise.resolve([]),
      ])

      setPosts(postsResponse)
      setMyPosts(myPostsResponse)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
    } finally {
      if (showLoading) {
        setIsLoading(false)
      }
    }
  }, [currentUser])

  useEffect(() => {
    let ignore = false

    async function loadInitialNeedASub() {
      if (isAuthLoading) {
        return
      }

      setIsLoading(true)
      setError('')

      try {
        const [postsResponse, myPostsResponse] = await Promise.all([
          listNeedASubPosts(),
          currentUser ? listMyNeedASubPosts(currentUser).catch(() => []) : Promise.resolve([]),
        ])

        if (!ignore) {
          setPosts(postsResponse)
          setMyPosts(myPostsResponse)
        }
      } catch (loadError) {
        if (!ignore) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load Need a Sub.')
        }
      } finally {
        if (!ignore) {
          setIsLoading(false)
        }
      }
    }

    loadInitialNeedASub()

    return () => {
      ignore = true
    }
  }, [currentUser, isAuthLoading])

  useEffect(() => {
    function refreshVisibleNeedASub() {
      if (document.visibilityState === 'visible') {
        refreshNeedASub()
      }
    }

    window.addEventListener('focus', refreshNeedASub)
    document.addEventListener('visibilitychange', refreshVisibleNeedASub)

    return () => {
      window.removeEventListener('focus', refreshNeedASub)
      document.removeEventListener('visibilitychange', refreshVisibleNeedASub)
    }
  }, [refreshNeedASub])

  const visiblePosts = postView === 'mine' ? myPosts : posts
  const totalSpotsNeeded = useMemo(
    () => form.positions.reduce((sum, position) => sum + Number(position.spots_needed || 0), 0),
    [form.positions],
  )

  function updateField(field, value) {
    setNotice('')
    setError('')
    setFormError('')
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function updateGamePlayerGroup(value) {
    setNotice('')
    setError('')
    setFormError('')
    setForm((currentForm) => ({
      ...currentForm,
      gamePlayerGroup: value,
      positions: getDefaultPositions(value),
    }))
  }

  function updatePosition(index, field, value) {
    setNotice('')
    setError('')
    setFormError('')
    setForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions.map((position, currentIndex) =>
        currentIndex === index
          ? { ...position, [field]: field === 'spots_needed' ? Number(value) : value }
          : position,
      ),
    }))
  }

  function addPosition() {
    setForm((currentForm) => ({
      ...currentForm,
      positions: [
        ...currentForm.positions,
        {
          ...getNextPosition(currentForm.positions, currentForm.gamePlayerGroup),
          spots_needed: 1,
          sort_order: currentForm.positions.length,
        },
      ],
    }))
  }

  function removePosition(index) {
    setForm((currentForm) => ({
      ...currentForm,
      positions: currentForm.positions
        .filter((_, currentIndex) => currentIndex !== index)
        .map((position, sortOrder) => ({ ...position, sort_order: sortOrder })),
    }))
  }

  function showBrowsePanel() {
    setNotice('')
    setError('')
    setFormError('')
    setActivePanel('browse')
  }

  function showCreatePanel() {
    setNotice('')
    setError('')
    setFormError('')
    setActivePanel('create')
  }

  function switchPostView(nextView) {
    setPostView(nextView)
    refreshNeedASub({ showLoading: true })
  }

  async function submitPost(event) {
    event.preventDefault()

    if (!currentUser) {
      navigate('/sign-in', { state: { from: '/need-a-sub' } })
      return
    }

    const validationError = validateNeedASubForm(form)
    if (validationError) {
      setFormError(validationError)
      return
    }

    setIsCreating(true)
    setError('')
    setNotice('')

    try {
      const payload = buildNeedASubPayload(form, totalSpotsNeeded)
      await createNeedASubPost(currentUser, payload)
      setPostView('mine')
      setForm(buildInitialNeedASubForm())
      setActivePanel('browse')
      setNotice('Post published.')
      await refreshNeedASub({ showLoading: true })
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to create post.')
    } finally {
      setIsCreating(false)
    }
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

function NeedASubPostList({
  isLoading,
  isSignedIn,
  onOpenPost,
  postView,
  posts,
}) {
  return (
    <section className="need-sub-panel">
      {postView === 'mine' && !isSignedIn ? (
        <NeedASubState
          title="Sign in to manage posts"
          message="Your created posts and request queues live behind your account."
          action={<Link to="/sign-in" state={{ from: '/need-a-sub' }}>Sign In</Link>}
        />
      ) : isLoading ? (
        <NeedASubState title="Loading Need a Sub posts" />
      ) : !posts.length ? (
        <NeedASubState
          title={postView === 'mine' ? 'No posts created yet' : 'No Need a Sub posts yet'}
          message={postView === 'mine' ? 'Create one when your team needs players.' : 'Check back soon or create your own post.'}
        />
      ) : (
        <div className="need-sub-post-grid">
          {posts.map((post) => {
            const playerTypeSummaries = buildPlayerTypeSummaries(post).filter(
              (summary) => summary.spotsLeft > 0,
            )
            const cityState = [post.city, post.state].filter(Boolean).join(', ')
            const environmentLabel = post.environment_type ? formatStatus(post.environment_type) : ''

            return (
              <article
                className="need-sub-post"
                key={post.id}
                role="button"
                tabIndex={0}
                onClick={() => onOpenPost(post)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onOpenPost(post)
                  }
                }}
              >
                <div className="need-sub-post__top">
                  <div className="need-sub-post__title-row">
                    <strong>
                      Need <span>{post.subs_needed}</span> {post.subs_needed === 1 ? 'Sub' : 'Subs'}
                    </strong>
                    {environmentLabel && (
                      <span className="need-sub-post__environment">{environmentLabel}</span>
                    )}
                  </div>
                  <small>{buildPostSubtitle(post)}</small>
                </div>

                <div className="need-sub-post__facts">
                  <Fact icon={<BuildingIcon />} text={post.location_name || 'Pickup Lane'} />
                  <Fact icon={<MapPinIcon />} text={cityState || 'Location not set'} />
                  <Fact icon={<CalendarIcon />} text={formatDateWithYear(post.starts_at)} />
                  <Fact icon={<ClockIcon />} text={formatTimeRangeOnly(post)} />
                </div>

                <div className="need-sub-post__needs">
                  {playerTypeSummaries.map((summary) => (
                    <span
                      className="need-sub-post__need-row"
                      key={summary.key}
                    >
                      <small>{summary.label}</small>
                      <strong>{formatOpenCount(summary.spotsLeft)}</strong>
                    </span>
                  ))}
                </div>

                <div className="need-sub-post__footer">
                  <span>
                    <UsersIcon />
                    {post.confirmed_count || 0}/{post.subs_needed} spots
                  </span>
                  <span className="need-sub-card-arrow" aria-hidden="true">›</span>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

function NeedASubState({ action = null, message = '', title }) {
  return (
    <div className="need-sub-state">
      <MapPinIcon />
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {action && <div className="need-sub-state__action">{action}</div>}
    </div>
  )
}

const PLAYER_TYPE_SUMMARY_ORDER = [
  { key: 'men', label: 'Men' },
  { key: 'women', label: 'Women' },
  { key: 'open', label: 'Any Player' },
]

function buildPlayerTypeSummaries(post) {
  const spotsByGroup = new Map(PLAYER_TYPE_SUMMARY_ORDER.map((group) => [group.key, 0]))

  ;(post.positions || []).forEach((position) => {
    const spotsLeft = Math.max(0, Number(position.spots_needed || 0) - countHeldSpots(position))
    spotsByGroup.set(position.player_group, (spotsByGroup.get(position.player_group) || 0) + spotsLeft)
  })

  return PLAYER_TYPE_SUMMARY_ORDER.map((group) => ({
    ...group,
    spotsLeft: spotsByGroup.get(group.key) || 0,
  }))
}

function formatOpenCount(spotsLeft) {
  return `${spotsLeft} open`
}

function Fact({ icon, text }) {
  return (
    <span>
      {icon}
      {text}
    </span>
  )
}

export default NeedASubPage
