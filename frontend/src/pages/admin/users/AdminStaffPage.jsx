import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, UsersRound } from 'lucide-react'
import { AppPageHeader, AppPageShell } from '../../../components/app/index.js'
import { SkeletonBlock } from '../../../components/skeleton/index.js'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminUsers.css'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import { listAdminStaff } from '../shared/adminApi.js'
import {
  formatAdminUserDateTime,
  formatAdminUserStatus,
  shortAdminUserId,
} from './adminUserFormatters.js'

function AdminStaffLoading() {
  return (
    <div className="admin-users-loading" role="status" aria-label="Loading staff">
      {Array.from({ length: 4 }).map((_, index) => (
        <div className="admin-users-loading__row" key={index}>
          <SkeletonBlock height="0.9rem" rounded width="44%" />
          <SkeletonBlock height="0.72rem" rounded width="58%" />
          <SkeletonBlock height="0.72rem" rounded width="30%" />
        </div>
      ))}
    </div>
  )
}

function AdminStaffList({ staff }) {
  if (!staff.length) {
    return (
      <div className="admin-users-empty">
        <strong>No staff accounts found</strong>
        <span>Admins and moderators will appear here.</span>
      </div>
    )
  }

  return (
    <div
      className="admin-users-table admin-users-table--staff"
      role="table"
      aria-label="Admin staff"
    >
      <div className="admin-users-table__header" role="row">
        <span role="columnheader">Staff</span>
        <span role="columnheader">Role</span>
        <span role="columnheader">Account</span>
        <span role="columnheader">Hosting</span>
        <span role="columnheader">Access</span>
      </div>
      {staff.map((staffUser) => (
        <Link
          aria-label={`Open ${staffUser.display_name}`}
          className="admin-users-table__row"
          key={staffUser.id}
          role="row"
          to={`/admin/users/${staffUser.id}`}
        >
          <div className="admin-users-table__identity" data-label="Staff" role="cell">
            <strong>{staffUser.display_name}</strong>
            <span>{staffUser.email || 'No email'}</span>
            <code>{staffUser.id}</code>
          </div>
          <div data-label="Role" role="cell">
            <span className="admin-users-status">
              {formatAdminUserStatus(staffUser.role)}
            </span>
            <span>{staffUser.email_verified ? 'Email verified' : 'Email unverified'}</span>
          </div>
          <div data-label="Account" role="cell">
            <span className={`admin-users-status admin-users-status--${staffUser.account_status}`}>
              {formatAdminUserStatus(staffUser.account_status)}
            </span>
            <span>Updated {formatAdminUserDateTime(staffUser.updated_at)}</span>
          </div>
          <div data-label="Hosting" role="cell">
            <span>{formatAdminUserStatus(staffUser.hosting_status)}</span>
            {staffUser.deleted_at && (
              <span>Deleted {formatAdminUserDateTime(staffUser.deleted_at)}</span>
            )}
          </div>
          <div data-label="Access" role="cell">
            <span>{staffUser.permissions.length} permissions</span>
            <span>{staffUser.data_scopes.length} scopes</span>
            <code>{shortAdminUserId(staffUser.id)}</code>
          </div>
        </Link>
      ))}
    </div>
  )
}

function AdminStaffPage() {
  const { currentUser } = useAuth()
  const [includeDeleted, setIncludeDeleted] = useState(false)
  const [staff, setStaff] = useState([])
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    let isMounted = true

    async function loadStaff() {
      if (!currentUser) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextStaff = await listAdminStaff({
          firebaseUser: currentUser,
          includeDeleted,
        })

        if (!isMounted) {
          return
        }

        setStaff(nextStaff)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setStaff([])
        setPageError(error.message || 'Staff accounts could not be loaded.')
        setLoadState('error')
      }
    }

    loadStaff()

    return () => {
      isMounted = false
    }
  }, [currentUser, includeDeleted, refreshCount])

  return (
    <AppPageShell className="admin-page" mainClassName="admin-shell admin-users-shell">
      <AppPageHeader subtitle="Admin Users" title="Staff" />

      <AdminWorkspaceLayout>
        <div className="admin-users-layout">
          <section className="admin-users-panel" aria-label="Staff list">
            <div className="admin-users-panel__heading">
              <div>
                <UsersRound />
                <h2>Staff accounts</h2>
              </div>
              <span>{loadState === 'ready' ? staff.length : 0} staff</span>
            </div>

            <div className="admin-users-staff-toolbar">
              <label className="admin-users-checkbox">
                <input
                  checked={includeDeleted}
                  type="checkbox"
                  onChange={(event) => setIncludeDeleted(event.target.checked)}
                />
                <span>Include deleted staff</span>
              </label>
              <button
                className="admin-users-button admin-users-button--icon"
                aria-label="Refresh staff"
                title="Refresh staff"
                type="button"
                onClick={() => setRefreshCount((count) => count + 1)}
              >
                <RefreshCw />
              </button>
            </div>

            {pageError && (
              <div className="admin-users-alert" role="alert">
                {pageError}
              </div>
            )}

            {loadState === 'loading' && <AdminStaffLoading />}
            {loadState === 'ready' && <AdminStaffList staff={staff} />}
          </section>
        </div>
      </AdminWorkspaceLayout>
    </AppPageShell>
  )
}

export default AdminStaffPage
