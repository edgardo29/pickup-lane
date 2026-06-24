import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  RefreshCw,
  RotateCcw,
  Search,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { AppPageShell } from '../../../components/app/index.js'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminNeedASub.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminNeedASubPosts } from '../shared/adminApi.js'
import {
  formatAdminNeedASubDateTime,
  formatAdminNeedASubStatus,
  shortAdminNeedASubId,
} from './adminNeedASubFormatters.js'

const STATUS_OPTIONS = [
  { label: 'All statuses', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Filled', value: 'filled' },
  { label: 'Expired', value: 'expired' },
  { label: 'Canceled', value: 'canceled' },
  { label: 'Removed', value: 'removed' },
]

const EMPTY_FILTERS = { postStatus: '', query: '' }
const PAGE_SIZE = 50

function AdminNeedASubLoading() {
  return (
    <div className="admin-sub-loading" role="status" aria-label="Loading Need a Sub posts">
      {Array.from({ length: 5 }).map((_, index) => (
        <div className="admin-sub-loading__row" key={index}>
          <SkeletonBlock height="0.9rem" rounded width="42%" />
          <SkeletonBlock height="0.72rem" rounded width="64%" />
          <SkeletonBlock height="0.72rem" rounded width="28%" />
        </div>
      ))}
    </div>
  )
}

function AdminNeedASubList({ posts }) {
  if (!posts.length) {
    return (
      <div className="admin-sub-empty">
        <strong>No Need a Sub posts found</strong>
        <span>Adjust the search or status filter.</span>
      </div>
    )
  }

  return (
    <div className="admin-sub-table" role="table" aria-label="Need a Sub posts">
      <div className="admin-sub-table__header" role="row">
        <span role="columnheader">Post</span>
        <span role="columnheader">Owner</span>
        <span role="columnheader">Requests</span>
        <span role="columnheader">Setup</span>
        <span role="columnheader">Status</span>
      </div>
      {posts.map((post) => (
        <Link
          className="admin-sub-table__row"
          key={post.id}
          role="row"
          to={`/admin/need-a-sub/${post.id}`}
        >
          <div data-label="Post" role="cell">
            <strong>{post.team_name || `Need ${post.subs_needed} Subs`}</strong>
            <span>{post.location_name} · {post.city}, {post.state}</span>
            <span>{formatAdminNeedASubDateTime(post.starts_at, post.timezone)}</span>
            <code>{shortAdminNeedASubId(post.id)}</code>
          </div>
          <div data-label="Owner" role="cell">
            <strong>{post.owner.display_name}</strong>
            <span>{formatAdminNeedASubStatus(post.owner.account_status)}</span>
          </div>
          <div data-label="Requests" role="cell">
            <strong>{post.request_counts.total_count} total</strong>
            <span>{post.request_counts.pending_count} pending</span>
            <span>{post.request_counts.confirmed_count} confirmed</span>
          </div>
          <div data-label="Setup" role="cell">
            <strong>{post.format_label} · {formatAdminNeedASubStatus(post.game_player_group)}</strong>
            <span>{formatAdminNeedASubStatus(post.environment_type)}</span>
            <span>{post.subs_needed} subs needed</span>
          </div>
          <div data-label="Status" role="cell">
            <span className={`admin-sub-status admin-sub-status--${post.post_status}`}>
              {formatAdminNeedASubStatus(post.post_status)}
            </span>
            <span>Updated {formatAdminNeedASubDateTime(post.updated_at, post.timezone)}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}

function AdminNeedASubPage() {
  const { currentUser } = useAuth()
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [posts, setPosts] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadPosts() {
      if (!currentUser) return
      setLoadState('loading')
      setPageError('')

      try {
        const response = await listAdminNeedASubPosts({
          firebaseUser: currentUser,
          limit: PAGE_SIZE,
          offset,
          ...appliedFilters,
        })
        if (!isMounted) return
        const nextPosts = response.posts ?? []
        const nextTotalCount = response.total_count ?? nextPosts.length
        if (!nextPosts.length && offset > 0 && nextTotalCount > 0) {
          setOffset(Math.max(0, offset - PAGE_SIZE))
          return
        }
        setPosts(nextPosts)
        setTotalCount(nextTotalCount)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) return
        setPosts([])
        setTotalCount(0)
        setPageError(error.message || 'Need a Sub posts could not be loaded.')
        setLoadState('error')
      }
    }

    loadPosts()
    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, offset, refreshCount])

  function handleSearch(event) {
    event.preventDefault()
    setOffset(0)
    setAppliedFilters({
      ...draftFilters,
      query: draftFilters.query.trim(),
    })
  }

  function handleReset() {
    setDraftFilters(EMPTY_FILTERS)
    setOffset(0)
    setAppliedFilters(EMPTY_FILTERS)
  }

  const pageStart = totalCount ? offset + 1 : 0
  const pageEnd = Math.min(offset + posts.length, totalCount)
  const hasPreviousPage = offset > 0
  const hasNextPage = offset + posts.length < totalCount

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell">
      <AdminWorkspaceLayout
        breadcrumbs={['Admin', 'Games', 'Need a Sub']}
        description="Find Need a Sub posts and review moderation activity."
        icon={ClipboardList}
        title="Need a Sub"
      >
        <section className="admin-sub-panel" aria-label="Need a Sub support">
          <div className="admin-sub-panel__heading">
            <div>
              <ClipboardList />
              <h2>Post support</h2>
            </div>
            <span>{loadState === 'ready' ? totalCount : 0} results</span>
          </div>
          <form className="admin-sub-filters" onSubmit={handleSearch}>
            <label>
              <span>Search</span>
              <input
                aria-label="Search by team, owner, location, or post ID"
                value={draftFilters.query}
                onChange={(event) => setDraftFilters((current) => ({
                  ...current,
                  query: event.target.value,
                }))}
              />
            </label>
            <label>
              <span>Status</span>
              <select
                value={draftFilters.postStatus}
                onChange={(event) => setDraftFilters((current) => ({
                  ...current,
                  postStatus: event.target.value,
                }))}
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value || 'all'} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="admin-sub-filter-actions">
              <button className="admin-sub-button" type="submit">
                <Search />
                Search
              </button>
              <button className="admin-sub-button" type="button" onClick={handleReset}>
                <RotateCcw />
                Reset
              </button>
              <button
                aria-label="Refresh Need a Sub posts"
                className="admin-sub-button admin-sub-button--icon"
                type="button"
                onClick={() => setRefreshCount((count) => count + 1)}
              >
                <RefreshCw />
              </button>
            </div>
          </form>
          {pageError && (
            <FormErrorMessage className="admin-sub-page-error">
              {pageError}
            </FormErrorMessage>
          )}
          {loadState === 'loading' ? (
            <AdminNeedASubLoading />
          ) : loadState === 'ready' ? (
            <>
              <AdminNeedASubList posts={posts} />
              {totalCount > PAGE_SIZE && (
                <nav aria-label="Need a Sub posts pagination" className="admin-sub-pagination">
                  <span>{pageStart}-{pageEnd} of {totalCount}</span>
                  <div>
                    <button
                      aria-label="Previous Need a Sub posts page"
                      className="admin-sub-button admin-sub-button--icon"
                      disabled={!hasPreviousPage}
                      title="Previous page"
                      type="button"
                      onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    >
                      <ChevronLeft />
                    </button>
                    <button
                      aria-label="Next Need a Sub posts page"
                      className="admin-sub-button admin-sub-button--icon"
                      disabled={!hasNextPage}
                      title="Next page"
                      type="button"
                      onClick={() => setOffset(offset + PAGE_SIZE)}
                    >
                      <ChevronRight />
                    </button>
                  </div>
                </nav>
              )}
            </>
          ) : null}
        </section>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminNeedASubPage
