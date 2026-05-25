import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth.js'

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

export function RequireAdmin({ children }) {
  const { appUser, isLoading } = useAuth()
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

  if (appUser.role !== 'admin') {
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
