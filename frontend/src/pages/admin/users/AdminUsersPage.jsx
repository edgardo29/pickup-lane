import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  CircleUserRound,
  RotateCcw,
  Search,
  UsersRound,
} from 'lucide-react'
import { FormErrorMessage } from '../../../components/FormErrorMessage.jsx'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminUsers.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminUsers } from '../shared/adminApi.js'
import {
  formatAdminUserDate,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

const PAGE_SIZE = 50

const ACCOUNT_STATUS_OPTIONS = [
  { label: 'All accounts', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Suspended', value: 'suspended' },
  { label: 'Pending deletion', value: 'pending_deletion' },
  { label: 'Deleted', value: 'deleted' },
]

const HOSTING_STATUS_OPTIONS = [
  { label: 'All hosting', value: '' },
  { label: 'Not eligible', value: 'not_eligible' },
  { label: 'Eligible', value: 'eligible' },
  { label: 'Restricted', value: 'restricted' },
]

const USER_VIEW_TABS = [
  { label: 'All users', role: '', value: 'all' },
  { label: 'Admins', role: 'admin', value: 'admins' },
]

function hasOptionValue(options, value) {
  return options.some((option) => option.value === value)
}

function readUsersFilters(searchParams) {
  const accountStatus = searchParams.get('account_status') || ''
  const hostingStatus = searchParams.get('hosting_status') || ''
  const role = searchParams.get('role') === 'admin' ? 'admin' : ''

  return {
    accountStatus: hasOptionValue(ACCOUNT_STATUS_OPTIONS, accountStatus)
      ? accountStatus
      : '',
    hostingStatus: hasOptionValue(HOSTING_STATUS_OPTIONS, hostingStatus)
      ? hostingStatus
      : '',
    query: searchParams.get('query') || '',
    role,
  }
}

function buildUsersSearchParams(filters) {
  const searchParams = new URLSearchParams()
  const query = filters.query.trim()

  if (query) {
    searchParams.set('query', query)
  }
  if (filters.accountStatus) {
    searchParams.set('account_status', filters.accountStatus)
  }
  if (filters.hostingStatus) {
    searchParams.set('hosting_status', filters.hostingStatus)
  }
  if (filters.role) {
    searchParams.set('role', filters.role)
  }

  return searchParams
}

function mergeUniqueUsers(currentUsers, nextUsers) {
  const seenIds = new Set(currentUsers.map((user) => user.id))
  const uniqueNextUsers = nextUsers.filter((user) => {
    if (seenIds.has(user.id)) {
      return false
    }
    seenIds.add(user.id)
    return true
  })

  return [...currentUsers, ...uniqueNextUsers]
}

function getUsersCountLabel(count, hasMore) {
  const noun = count === 1 ? 'user' : 'users'
  return `${count} ${noun} shown${hasMore ? '+' : ''}`
}

function AdminUsersLoading() {
  return (
    <div className="admin-users-loading" role="status" aria-label="Loading users">
      {Array.from({ length: 6 }).map((_, index) => (
        <div className="admin-users-loading__card" key={index}>
          <SkeletonBlock height="0.68rem" rounded width="22%" />
          <SkeletonBlock height="1rem" rounded width="58%" />
          <SkeletonBlock height="0.68rem" rounded width="18%" />
          <SkeletonBlock height="0.92rem" rounded width="72%" />
        </div>
      ))}
    </div>
  )
}

function AdminUsersEmpty() {
  return (
    <div className="admin-users-empty">
      <strong>No users found</strong>
      <span>Adjust the filters and search again.</span>
    </div>
  )
}

function AdminUserCardFact({ className = '', label, value }) {
  return (
    <div className={`admin-users-card__fact ${className}`}>
      <span>{label}</span>
      {value}
    </div>
  )
}

function AdminUsersList({ users }) {
  return (
    <div className="admin-users-card-grid" aria-label="User directory results">
      {users.map((user) => {
        const hostingStatus = user.hosting_status || 'not_eligible'

        return (
          <Link
            className="admin-users-card"
            key={user.id}
            to={`/admin/users/${user.id}`}
          >
            <span className="admin-users-card__icon" aria-hidden="true">
              <CircleUserRound />
            </span>
            <div className="admin-users-card__facts">
              <AdminUserCardFact
                className="admin-users-card__fact--wide admin-users-card__fact--with-icon"
                label="Full name"
                value={<strong>{user.display_name}</strong>}
              />
              <AdminUserCardFact
                className="admin-users-card__fact--wide"
                label="Email"
                value={<strong>{user.email || 'No email'}</strong>}
              />
              <AdminUserCardFact
                label="Role"
                value={
                  <strong>{formatAdminUserStatus(user.role)}</strong>
                }
              />
              <AdminUserCardFact
                label="Account"
                value={
                  <strong>{formatAdminUserStatus(user.account_status)}</strong>
                }
              />
              <AdminUserCardFact
                label="Hosting"
                value={
                  <strong>{formatAdminUserStatus(hostingStatus)}</strong>
                }
              />
              <AdminUserCardFact
                label="Member since"
                value={
                  <strong>
                    {formatAdminUserDate(user.member_since)}
                  </strong>
                }
              />
            </div>
          </Link>
        )
      })}
    </div>
  )
}

function AdminUsersPage() {
  const { currentUser } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const searchParamsKey = searchParams.toString()
  const appliedFilters = useMemo(
    () => readUsersFilters(new URLSearchParams(searchParamsKey)),
    [searchParamsKey],
  )
  const [draftFilters, setDraftFilters] = useState(appliedFilters)
  const [users, setUsers] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [nextCursor, setNextCursor] = useState('')
  const [hasMoreUsers, setHasMoreUsers] = useState(false)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [loadMoreError, setLoadMoreError] = useState('')
  const requestIdRef = useRef(0)
  const activeView = appliedFilters.role === 'admin' ? 'admins' : 'all'
  const countLabel = getUsersCountLabel(users.length, hasMoreUsers)
  const includeDeletedUsers = appliedFilters.accountStatus === 'deleted'

  useEffect(() => {
    let isActive = true

    Promise.resolve().then(() => {
      if (isActive) {
        setDraftFilters(appliedFilters)
      }
    })

    return () => {
      isActive = false
    }
  }, [appliedFilters])

  useEffect(() => {
    let isMounted = true
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId

    Promise.resolve()
      .then(() => {
        if (!isMounted || requestId !== requestIdRef.current) {
          return null
        }

        setLoadState('loading')
        setPageError('')
        setLoadMoreError('')
        setUsers([])
        setNextCursor('')
        setHasMoreUsers(false)
        setIsLoadingMore(false)

        return listAdminUsers({
          accountStatus: appliedFilters.accountStatus,
          firebaseUser: currentUser,
          hostingStatus: appliedFilters.hostingStatus,
          includeDeleted: includeDeletedUsers,
          limit: PAGE_SIZE,
          query: appliedFilters.query,
          role: appliedFilters.role,
        })
      })
      .then((response) => {
        if (!response) {
          return
        }
        if (!isMounted || requestId !== requestIdRef.current) {
          return
        }

        setUsers(response.users ?? [])
        setNextCursor(response.next_cursor ?? '')
        setHasMoreUsers(Boolean(response.has_more))
        setLoadState('ready')
      })
      .catch((error) => {
        if (!isMounted || requestId !== requestIdRef.current) {
          return
        }

        setPageError(error.message || 'Users could not be loaded.')
        setLoadState('error')
      })

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, includeDeletedUsers])

  function updateFilters(nextFilters) {
    setSearchParams(buildUsersSearchParams(nextFilters))
  }

  function handleSubmit(event) {
    event.preventDefault()
    updateFilters({
      ...draftFilters,
      query: draftFilters.query.trim(),
    })
  }

  function handleReset() {
    const emptyFilters = {
      accountStatus: '',
      hostingStatus: '',
      query: '',
      role: appliedFilters.role,
    }
    setDraftFilters(emptyFilters)
    updateFilters(emptyFilters)
  }

  function handleViewChange(view) {
    const tab = USER_VIEW_TABS.find((item) => item.value === view)
    if (!tab) {
      return
    }

    const nextFilters = {
      ...appliedFilters,
      role: tab.role,
    }
    setDraftFilters(nextFilters)
    updateFilters(nextFilters)
  }

  function loadMoreUsers() {
    if (!currentUser || !hasMoreUsers || !nextCursor || isLoadingMore) {
      return
    }

    setIsLoadingMore(true)
    setLoadMoreError('')
    const requestId = requestIdRef.current

    listAdminUsers({
      accountStatus: appliedFilters.accountStatus,
      cursor: nextCursor,
      firebaseUser: currentUser,
      hostingStatus: appliedFilters.hostingStatus,
      includeDeleted: includeDeletedUsers,
      limit: PAGE_SIZE,
      query: appliedFilters.query,
      role: appliedFilters.role,
    })
      .then((response) => {
        if (requestId !== requestIdRef.current) {
          return
        }

        setUsers((currentUsers) =>
          mergeUniqueUsers(currentUsers, response.users ?? []),
        )
        setNextCursor(response.next_cursor ?? '')
        setHasMoreUsers(Boolean(response.has_more))
      })
      .catch((error) => {
        if (requestId !== requestIdRef.current) {
          return
        }

        setLoadMoreError(error.message || 'More users could not be loaded.')
      })
      .finally(() => {
        if (requestId !== requestIdRef.current) {
          return
        }

        setIsLoadingMore(false)
      })
  }

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'People', 'User Directory']}
      description="Search accounts, review role access, hosting status, and account state."
      icon={UsersRound}
      title="User Directory"
    >
      <section className="admin-users-directory" aria-label="User Directory">
        <div
          className="admin-users-view-tabs pl-scrollbar"
          aria-label="User views"
          role="tablist"
        >
          {USER_VIEW_TABS.map((tab) => (
            <button
              aria-selected={activeView === tab.value}
              className={activeView === tab.value ? 'is-active' : ''}
              key={tab.value}
              onClick={() => handleViewChange(tab.value)}
              role="tab"
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        <form
          className="admin-users-filters"
          aria-label="User directory filters"
          onSubmit={handleSubmit}
        >
          <label className="admin-users-filters__search">
            <span>Search</span>
            <input
              aria-label="Search users"
              maxLength={120}
              placeholder="Name, email, or user ID"
              type="text"
              value={draftFilters.query}
              onChange={(event) =>
                setDraftFilters((currentFilters) => ({
                  ...currentFilters,
                  query: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Account</span>
            <select
              value={draftFilters.accountStatus}
              onChange={(event) =>
                setDraftFilters((currentFilters) => ({
                  ...currentFilters,
                  accountStatus: event.target.value,
                }))
              }
            >
              {ACCOUNT_STATUS_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Hosting</span>
            <select
              value={draftFilters.hostingStatus}
              onChange={(event) =>
                setDraftFilters((currentFilters) => ({
                  ...currentFilters,
                  hostingStatus: event.target.value,
                }))
              }
            >
              {HOSTING_STATUS_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="admin-users-filter-actions">
            <button className="admin-users-button" type="submit">
              <Search aria-hidden="true" />
              Search
            </button>
            <button
              className="admin-users-button"
              type="button"
              onClick={handleReset}
            >
              <RotateCcw aria-hidden="true" />
              Reset
            </button>
          </div>
        </form>

        {pageError && (
          <div className="admin-users-alert">
            <FormErrorMessage>{pageError}</FormErrorMessage>
          </div>
        )}

        {loadState === 'loading' && <AdminUsersLoading />}
        {loadState === 'ready' && users.length === 0 && <AdminUsersEmpty />}
        {loadState === 'ready' && users.length > 0 && (
          <>
            <div className="admin-users-count-row">
              <span>{countLabel}</span>
            </div>
            <AdminUsersList users={users} />
            {(loadMoreError || hasMoreUsers) && (
              <nav className="admin-users-pagination" aria-label="User result pagination">
                {loadMoreError && (
                  <div className="admin-users-pagination__error">
                    <FormErrorMessage>{loadMoreError}</FormErrorMessage>
                  </div>
                )}
                <button
                  className="admin-users-button"
                  disabled={isLoadingMore}
                  type="button"
                  onClick={loadMoreUsers}
                >
                  {isLoadingMore ? 'Loading...' : 'Load more'}
                </button>
              </nav>
            )}
          </>
        )}
      </section>
    </AdminWorkspaceLayout>
  )
}

export default AdminUsersPage
