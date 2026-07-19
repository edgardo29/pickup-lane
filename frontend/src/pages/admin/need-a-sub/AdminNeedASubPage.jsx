import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ClipboardList,
  Search,
  X,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import {
  AddressIcon,
  GameDateIcon,
  GameSpotsIcon,
  GameTimeIcon,
  VenueIcon,
} from '../../../components/GameFactIcons.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminNeedASub.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminNeedASubPosts } from '../shared/adminApi.js'
import { formatAdminNeedASubStatus } from './adminNeedASubFormatters.js'

const needASubViewTabs = [
  { key: 'active', label: 'Active' },
  { key: 'full', label: 'Full' },
  { key: 'completed', label: 'Completed' },
  { key: 'cancelled', label: 'Cancelled' },
  { key: 'expired', label: 'Expired' },
  { key: 'removed', label: 'Removed' },
]

const PAGE_SIZE = 24
const SEARCH_DEBOUNCE_MS = 300
const SEARCH_MIN_LENGTH = 3
const SEARCH_MAX_LENGTH = 120
const fallbackTimeZone = 'America/Chicago'

function useDebouncedValue(value, delayMs) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedValue(value)
    }, delayMs)

    return () => window.clearTimeout(timeoutId)
  }, [delayMs, value])

  return debouncedValue
}

function getPostTimeZone(post) {
  return post.timezone || fallbackTimeZone
}

function getSubLabel(count) {
  return count === 1 ? 'Sub' : 'Subs'
}

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

function getPostTitle(post) {
  return `Need ${post.subs_needed} ${getSubLabel(post.subs_needed)}`
}

function getLocationLine(post) {
  return [post.city, post.state].filter(Boolean).join(', ') || 'Location unavailable'
}

function formatPostTimeRange(post) {
  if (!post.starts_at) {
    return 'Time unavailable'
  }

  const formatter = new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: getPostTimeZone(post),
  })

  if (!post.ends_at) {
    return formatter.format(new Date(post.starts_at))
  }

  return `${formatter.format(new Date(post.starts_at))} - ${formatter.format(
    new Date(post.ends_at),
  )}`
}

function getLocalDateKey(post) {
  if (post.starts_on_local) {
    return post.starts_on_local
  }

  if (!post.starts_at) {
    return 'unknown'
  }

  const parts = new Intl.DateTimeFormat('en-US', {
    day: '2-digit',
    month: '2-digit',
    timeZone: getPostTimeZone(post),
    year: 'numeric',
  }).formatToParts(new Date(post.starts_at))

  const dateParts = Object.fromEntries(
    parts.filter((part) => part.type !== 'literal').map((part) => [
      part.type,
      part.value,
    ]),
  )

  return `${dateParts.year}-${dateParts.month}-${dateParts.day}`
}

function formatDateGroupLabel(post) {
  if (post.starts_on_local) {
    return new Intl.DateTimeFormat(undefined, {
      day: 'numeric',
      month: 'short',
      timeZone: 'UTC',
      weekday: 'short',
      year: 'numeric',
    }).format(new Date(`${post.starts_on_local}T12:00:00Z`)).toUpperCase()
  }

  if (!post.starts_at) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    timeZone: getPostTimeZone(post),
    weekday: 'short',
    year: 'numeric',
  }).format(new Date(post.starts_at)).toUpperCase()
}

function groupPostsByDate(posts) {
  const groups = []
  const groupsByKey = new Map()

  posts.forEach((post) => {
    const key = getLocalDateKey(post)

    if (!groupsByKey.has(key)) {
      const group = {
        key,
        label: formatDateGroupLabel(post),
        posts: [],
      }
      groupsByKey.set(key, group)
      groups.push(group)
    }

    groupsByKey.get(key).posts.push(post)
  })

  return groups
}

function getPostSignals(post) {
  const signals = []

  if (post.public_visibility_status === 'hidden') {
    signals.push('Hidden')
  }

  if (post.post_status && post.post_status !== 'active') {
    signals.push(formatAdminNeedASubStatus(post.post_status))
  }

  if (post.request_counts.pending_count > 0) {
    signals.push(`${pluralize(post.request_counts.pending_count, 'pending request')}`)
  }

  if (post.request_counts.confirmed_count > 0) {
    signals.push(`${pluralize(post.request_counts.confirmed_count, 'confirmed request')}`)
  }

  return signals
}

function getCountLabel(visibleCount, totalCount) {
  if (!totalCount) {
    return '0 posts'
  }

  if (visibleCount >= totalCount) {
    return `${totalCount} ${totalCount === 1 ? 'post' : 'posts'}`
  }

  return `Showing ${visibleCount} of ${totalCount} posts`
}

function AdminNeedASubLoading() {
  return (
    <div className="admin-sub-date-groups admin-sub-date-groups--skeleton" role="status" aria-label="Loading Need a Sub posts">
      <section className="admin-sub-date-group">
        <div className="admin-sub-date-group__header">
          <SkeletonBlock height="1rem" rounded width="12rem" />
        </div>
        <div className="admin-sub-card-grid">
          {Array.from({ length: 8 }).map((_, index) => (
            <article className="admin-sub-post-card admin-sub-post-card--skeleton" key={index}>
              <div className="admin-sub-post-card__body">
                <SkeletonBlock height="1rem" rounded width="82%" />
                <SkeletonBlock height="0.78rem" rounded width="54%" />
                <SkeletonBlock height="0.78rem" rounded width="62%" />
                <SkeletonBlock height="0.78rem" rounded width="46%" />
              </div>
              <div className="admin-sub-post-card__signals" />
              <div className="admin-sub-post-card__footer">
                <SkeletonBlock height="0.84rem" rounded width="5.8rem" />
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}

function AdminNeedASubPostCard({ post }) {
  const signals = getPostSignals(post)
  const subsNeeded = post.subs_needed
  const confirmedCount = post.request_counts.confirmed_count

  return (
    <Link
      aria-label={`Open ${getPostTitle(post)}`}
      className="admin-sub-post-card"
      to={`/admin/need-a-sub/${post.id}`}
    >
      <div className="admin-sub-post-card__body">
        <div className="admin-sub-post-card__identity">
          <h3>
            Need <span>{subsNeeded}</span> {getSubLabel(subsNeeded)}
          </h3>
          <p className="admin-sub-post-card__owner">
            <span>Owner: {post.owner.display_name}</span>
          </p>
        </div>

        <div className="admin-sub-post-card__details">
          <p className="admin-sub-post-card__venue">
            <VenueIcon aria-hidden="true" />
            <span>{post.location_name || 'Venue unavailable'}</span>
          </p>
          <p>
            <AddressIcon aria-hidden="true" />
            <span>{getLocationLine(post)}</span>
          </p>
          <p>
            <GameTimeIcon aria-hidden="true" />
            <span>{formatPostTimeRange(post)}</span>
          </p>
        </div>
      </div>

      <div
        aria-label={signals.length ? 'Need a Sub post signals' : undefined}
        className={
          signals.length
            ? 'admin-sub-post-card__signals admin-sub-post-card__signals--active'
            : 'admin-sub-post-card__signals'
        }
      >
        {signals.slice(0, 2).map((signal) => (
          <span key={signal}>{signal}</span>
        ))}
      </div>

      <div className="admin-sub-post-card__footer">
        <span className="admin-sub-post-card__capacity">
          <GameSpotsIcon aria-hidden="true" />
          <span className="admin-sub-post-card__capacity-copy">
            <strong>{confirmedCount}/{subsNeeded}</strong> spots
          </span>
        </span>
      </div>
    </Link>
  )
}

function AdminNeedASubList({ posts, hasFilters = false }) {
  if (!posts.length) {
    return (
      <div className="admin-sub-empty">
        <ClipboardList aria-hidden="true" />
        <strong>No Need a Sub posts found</strong>
        <span>
          {hasFilters
            ? 'Try clearing the search or changing views.'
            : 'Need a Sub posts will appear here after players publish them.'}
        </span>
      </div>
    )
  }

  const groupedPosts = groupPostsByDate(posts)

  return (
    <div className="admin-sub-date-groups">
      {groupedPosts.map((group) => (
        <section className="admin-sub-date-group" key={group.key}>
          <div className="admin-sub-date-group__header">
            <h3>
              <GameDateIcon aria-hidden="true" />
              {group.label}
            </h3>
            <span>{group.posts.length} {group.posts.length === 1 ? 'post' : 'posts'}</span>
          </div>

          <div className="admin-sub-card-grid">
            {group.posts.map((post) => (
              <AdminNeedASubPostCard key={post.id} post={post} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function AdminNeedASubPage() {
  const { currentUser } = useAuth()
  const [searchInput, setSearchInput] = useState('')
  const [activeView, setActiveView] = useState('active')
  const [posts, setPosts] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [loadState, setLoadState] = useState('loading')
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [pageError, setPageError] = useState('')
  const [loadMoreError, setLoadMoreError] = useState('')
  const [nextCursor, setNextCursor] = useState('')
  const [hasMorePosts, setHasMorePosts] = useState(false)
  const requestIdRef = useRef(0)
  const debouncedSearchInput = useDebouncedValue(
    searchInput.trim(),
    SEARCH_DEBOUNCE_MS,
  )
  const activeSearch =
    debouncedSearchInput.length >= SEARCH_MIN_LENGTH ? debouncedSearchInput : ''

  useEffect(() => {
    let isMounted = true
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId

    async function loadPosts() {
      if (!currentUser) return
      setLoadState('loading')
      setPosts([])
      setPageError('')
      setLoadMoreError('')
      setNextCursor('')
      setHasMorePosts(false)

      try {
        const response = await listAdminNeedASubPosts({
          firebaseUser: currentUser,
          limit: PAGE_SIZE,
          offset: 0,
          query: activeSearch,
          view: activeView,
        })
        if (!isMounted || requestId !== requestIdRef.current) return
        const nextPosts = response.posts ?? []
        const nextTotalCount = response.total_count ?? nextPosts.length
        setPosts(nextPosts)
        setTotalCount(nextTotalCount)
        setNextCursor(response.next_cursor ?? '')
        setHasMorePosts(Boolean(response.has_more))
        setLoadState('ready')
      } catch (error) {
        if (!isMounted || requestId !== requestIdRef.current) return
        setPosts([])
        setTotalCount(0)
        setNextCursor('')
        setHasMorePosts(false)
        setPageError(error.message || 'Need a Sub posts could not be loaded.')
        setLoadState('error')
      }
    }

    loadPosts()
    return () => {
      isMounted = false
    }
  }, [activeSearch, activeView, currentUser])

  async function loadMorePosts() {
    if (!currentUser || isLoadingMore || !hasMorePosts) {
      return
    }

    setIsLoadingMore(true)
    setLoadMoreError('')

    try {
      const response = await listAdminNeedASubPosts({
        firebaseUser: currentUser,
        limit: PAGE_SIZE,
        cursor: nextCursor,
        offset: posts.length,
        query: activeSearch,
        view: activeView,
      })

      const nextPosts = response.posts ?? []
      setPosts((currentPosts) => [...currentPosts, ...nextPosts])
      setTotalCount(response.total_count ?? totalCount)
      setNextCursor(response.next_cursor ?? '')
      setHasMorePosts(Boolean(response.has_more))
    } catch (error) {
      setLoadMoreError(error.message || 'More Need a Sub posts could not be loaded.')
    } finally {
      setIsLoadingMore(false)
    }
  }

  const hasFilters = Boolean(activeSearch || activeView !== 'active')
  const countLabel = getCountLabel(posts.length, totalCount)

  return (
    <>
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Games', 'Need a Sub']}
        description="Find Need a Sub posts and review moderation activity."
        icon={ClipboardList}
        title="Need a Sub"
      >
        <section className="admin-sub-panel admin-sub-panel--list" aria-label="Need a Sub support">
          <div className="admin-sub-view-tabs" aria-label="Need a Sub views" role="tablist">
            {needASubViewTabs.map((tab) => (
              <button
                aria-selected={activeView === tab.key}
                className={activeView === tab.key ? 'is-active' : ''}
                key={tab.key}
                onClick={() => {
                  if (activeView !== tab.key) {
                    setActiveView(tab.key)
                  }
                }}
                role="tab"
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="admin-sub-filters" aria-label="Need a Sub filters">
            <label className="admin-sub-filters__search">
              <span className="admin-sub-sr-only">Search</span>
              <Search aria-hidden="true" />
              <input
                aria-label="Search by team, owner, or location"
                maxLength={SEARCH_MAX_LENGTH}
                placeholder="Search team, owner, or location..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
              {searchInput && (
                <button aria-label="Clear search" type="button" onClick={() => setSearchInput('')}>
                  <X aria-hidden="true" />
                </button>
              )}
            </label>
          </div>

          <div className="admin-sub-count-row">
            <span>{loadState === 'ready' ? countLabel : 'Loading posts'}</span>
          </div>

          {pageError && (
            <FormErrorMessage className="admin-sub-page-error">
              {pageError}
            </FormErrorMessage>
          )}
          {loadState === 'loading' ? (
            <AdminNeedASubLoading />
          ) : loadState === 'ready' ? (
            <>
              <AdminNeedASubList posts={posts} hasFilters={hasFilters} />
              {loadMoreError && (
                <FormErrorMessage className="admin-sub-load-more-error">
                  {loadMoreError}
                </FormErrorMessage>
              )}
              {hasMorePosts && (
                <div className="admin-sub-load-more">
                  <button
                    className="admin-sub-button admin-sub-button--load-more"
                    disabled={isLoadingMore}
                    type="button"
                    onClick={loadMorePosts}
                  >
                    {isLoadingMore ? 'Loading...' : 'Load more'}
                  </button>
                </div>
              )}
            </>
          ) : null}
        </section>
      </AdminWorkspaceLayout>
    </>
  )
}

export default AdminNeedASubPage
