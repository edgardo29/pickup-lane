import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, RotateCcw, Search, UsersRound } from 'lucide-react'
import { AppPageHeader, AppPageShell } from '../../../components/app/index.js'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminUsers.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminUsers } from '../shared/adminApi.js'
import {
  formatAdminUserDate,
  formatAdminUserLocation,
  formatAdminUserStatus,
} from './adminUserFormatters.js'

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
  { label: 'Pending review', value: 'pending_review' },
  { label: 'Eligible', value: 'eligible' },
  { label: 'Restricted', value: 'restricted' },
  { label: 'Suspended', value: 'suspended' },
  { label: 'Banned', value: 'banned_from_hosting' },
]

const ROLE_OPTIONS = [
  { label: 'All roles', value: '' },
  { label: 'Player', value: 'player' },
  { label: 'Admin', value: 'admin' },
  { label: 'Moderator', value: 'moderator' },
]

const EMPTY_FILTERS = {
  accountStatus: '',
  hostingStatus: '',
  includeDeleted: false,
  query: '',
  role: '',
}

function AdminUsersLoading() {
  return (
    <div className="admin-users-loading" role="status" aria-label="Loading users">
      {Array.from({ length: 5 }).map((_, index) => (
        <div className="admin-users-loading__row" key={index}>
          <SkeletonBlock height="0.9rem" rounded width="46%" />
          <SkeletonBlock height="0.72rem" rounded width="62%" />
          <SkeletonBlock height="0.72rem" rounded width="34%" />
        </div>
      ))}
    </div>
  )
}

function AdminUsersList({ users }) {
  if (!users.length) {
    return (
      <div className="admin-users-empty">
        <strong>No users found</strong>
        <span>Adjust the search or filters.</span>
      </div>
    )
  }

  return (
    <div className="admin-users-table" role="table" aria-label="Admin users">
      <div className="admin-users-table__header" role="row">
        <span role="columnheader">User</span>
        <span role="columnheader">Account</span>
        <span role="columnheader">Hosting</span>
        <span role="columnheader">Location</span>
        <span role="columnheader">Member</span>
      </div>
      {users.map((user) => (
        <Link
          aria-label={`Open ${user.display_name}`}
          className="admin-users-table__row"
          key={user.id}
          role="row"
          to={`/admin/users/${user.id}`}
        >
          <div className="admin-users-table__identity" data-label="User" role="cell">
            <strong>{user.display_name}</strong>
            <span>{user.email || 'No email'}</span>
            <span>{user.phone || 'No phone'}</span>
            <code>{user.id}</code>
          </div>
          <div data-label="Account" role="cell">
            <span className={`admin-users-status admin-users-status--${user.account_status}`}>
              {formatAdminUserStatus(user.account_status)}
            </span>
            <span>{formatAdminUserStatus(user.role)}</span>
            <span>{user.email_verified ? 'Email verified' : 'Email unverified'}</span>
          </div>
          <div data-label="Hosting" role="cell">
            <span className="admin-users-status">
              {formatAdminUserStatus(user.hosting_status)}
            </span>
          </div>
          <div data-label="Location" role="cell">
            <span>{formatAdminUserLocation(user)}</span>
          </div>
          <div data-label="Member" role="cell">
            <span>{formatAdminUserDate(user.member_since)}</span>
            {user.deleted_at && (
              <span>Deleted {formatAdminUserDate(user.deleted_at)}</span>
            )}
          </div>
        </Link>
      ))}
    </div>
  )
}

function AdminUsersPage() {
  const { currentUser } = useAuth()
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS)
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS)
  const [users, setUsers] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadUsers() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextUsers = await listAdminUsers({
          firebaseUser: currentUser,
          ...appliedFilters,
        })

        if (!isMounted) {
          return
        }

        setUsers(nextUsers)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setUsers([])
        setPageError(error.message || 'Users could not be loaded.')
        setLoadState('error')
      }
    }

    loadUsers()

    return () => {
      isMounted = false
    }
  }, [appliedFilters, currentUser, refreshCount])

  function updateDraftFilter(field, value) {
    setDraftFilters((current) => ({
      ...current,
      ...(field === 'accountStatus' && value === 'deleted' ? { includeDeleted: true } : {}),
      ...(field === 'includeDeleted' && !value && current.accountStatus === 'deleted'
        ? { accountStatus: '' }
        : {}),
      [field]: value,
    }))
  }

  function handleSearch(event) {
    event.preventDefault()
    setAppliedFilters({
      ...draftFilters,
      query: draftFilters.query.trim(),
    })
  }

  function handleReset() {
    setDraftFilters(EMPTY_FILTERS)
    setAppliedFilters(EMPTY_FILTERS)
  }

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-users-shell">
      <AppPageHeader subtitle="Admin" title="Users" />

      <AdminWorkspaceLayout>
        <div className="admin-users-layout">
          <section className="admin-users-panel" aria-label="User search">
            <div className="admin-users-panel__heading">
              <div>
                <UsersRound />
                <h2>User directory</h2>
              </div>
              <span>{loadState === 'ready' ? users.length : 0} results</span>
            </div>

            <form className="admin-users-filters" onSubmit={handleSearch}>
              <label className="admin-users-filters__search">
                <span>Search</span>
                <input
                  aria-label="Search by name, email, phone, or user ID"
                  value={draftFilters.query}
                  onChange={(event) => updateDraftFilter('query', event.target.value)}
                />
              </label>
              <label>
                <span>Account</span>
                <select
                  value={draftFilters.accountStatus}
                  onChange={(event) => updateDraftFilter('accountStatus', event.target.value)}
                >
                  {ACCOUNT_STATUS_OPTIONS.map((option) => (
                    <option key={option.label} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Hosting</span>
                <select
                  value={draftFilters.hostingStatus}
                  onChange={(event) => updateDraftFilter('hostingStatus', event.target.value)}
                >
                  {HOSTING_STATUS_OPTIONS.map((option) => (
                    <option key={option.label} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                <span>Role</span>
                <select
                  value={draftFilters.role}
                  onChange={(event) => updateDraftFilter('role', event.target.value)}
                >
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option.label} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="admin-users-checkbox">
                <input
                  checked={draftFilters.includeDeleted}
                  type="checkbox"
                  onChange={(event) => updateDraftFilter('includeDeleted', event.target.checked)}
                />
                <span>Include deleted</span>
              </label>
              <div className="admin-users-filter-actions">
                <button className="admin-users-button" type="submit">
                  <Search />
                  Search
                </button>
                <button className="admin-users-button" type="button" onClick={handleReset}>
                  <RotateCcw />
                  Reset
                </button>
                <button
                  className="admin-users-button admin-users-button--icon"
                  aria-label="Refresh users"
                  title="Refresh users"
                  type="button"
                  onClick={() => setRefreshCount((count) => count + 1)}
                >
                  <RefreshCw />
                </button>
              </div>
            </form>

            {pageError && (
              <div className="admin-users-alert" role="alert">
                {pageError}
              </div>
            )}

            {loadState === 'loading' && <AdminUsersLoading />}
            {loadState === 'ready' && <AdminUsersList users={users} />}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminUsersPage
