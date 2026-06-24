import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'
import {
  ADMIN_PERMISSIONS,
  hasAnyAdminPermission,
} from '../pages/admin/shared/adminWorkspaceData.js'
import { useAdminAccess } from '../pages/admin/shared/useAdminAccess.js'
import '../styles/admin/AdminWorkspace.css'

function isAdminAccessDeniedError(error) {
  return error?.status === 401 || error?.status === 403
}

function AdminAccessRetryState({ onRetry }) {
  return (
    <main className="admin-guard-state" role="alert">
      <section className="admin-guard-state__panel">
        <h1>Could not verify staff access</h1>
        <p>Check your connection and try again.</p>
        <button type="button" onClick={onRetry}>
          Try again
        </button>
      </section>
    </main>
  )
}

export function RequireAppUser({ children }) {
  const { appUser, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return null
  }

  if (!appUser) {
    return (
      <Navigate
        to="/sign-in"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  }

  return children
}

export function RequireAdmin({
  children,
  permission = ADMIN_PERMISSIONS.ACTION_CENTER_VIEW,
  permissions = null,
}) {
  const { appUser, isLoading } = useAuth()
  const {
    adminAccess,
    error,
    isLoading: isAdminAccessLoading,
    reload,
  } = useAdminAccess({ enabled: Boolean(appUser) })
  const location = useLocation()

  if (isLoading) {
    return null
  }

  if (!appUser) {
    return (
      <Navigate
        to="/admin/sign-in"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  }

  if (isAdminAccessLoading) {
    return null
  }

  const requiredPermissions = permissions || [permission]

  if (error) {
    if (!isAdminAccessDeniedError(error)) {
      return <AdminAccessRetryState onRetry={reload} />
    }

    return (
      <Navigate
        to="/admin/sign-in"
        replace
        state={{
          adminDenied: true,
          from: `${location.pathname}${location.search}`,
        }}
      />
    )
  }

  if (!hasAnyAdminPermission(adminAccess, requiredPermissions)) {
    return (
      <Navigate
        to="/admin/sign-in"
        replace
        state={{
          adminDenied: true,
          from: `${location.pathname}${location.search}`,
        }}
      />
    )
  }

  return children
}

export function RedirectSignedIn({ children }) {
  const { appUser, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return null
  }

  if (appUser) {
    const returnPath = typeof location.state?.from === 'string' ? location.state.from : ''
    return <Navigate to={returnPath || '/games'} replace />
  }

  return children
}
