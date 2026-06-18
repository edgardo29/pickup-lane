import { useEffect, useState } from 'react'
import { useAuth } from '../../../hooks/useAuth.js'
import { fetchAdminMe } from './adminApi.js'
import { hasAdminPermission } from './adminWorkspaceData.js'

export function useAdminAccess({ enabled = true, reloadKey = 0 } = {}) {
  const { appUser, currentUser, isLoading: isAuthLoading } = useAuth()
  const [adminAccess, setAdminAccess] = useState(null)
  const [loadState, setLoadState] = useState('idle')
  const [error, setError] = useState(null)
  const isWaitingToLoad = (
    enabled
    && Boolean(appUser)
    && !error
    && (isAuthLoading || !currentUser || loadState === 'idle' || loadState === 'loading')
  )

  useEffect(() => {
    let ignore = false

    async function loadAdminAccess() {
      if (!enabled) {
        setAdminAccess(null)
        setError(null)
        setLoadState('idle')
        return
      }

      if (isAuthLoading) {
        return
      }

      if (!appUser || !currentUser) {
        setAdminAccess(null)
        setError(null)
        setLoadState('idle')
        return
      }

      setLoadState('loading')
      setError(null)

      try {
        const nextAdminAccess = await fetchAdminMe({ firebaseUser: currentUser })

        if (ignore) {
          return
        }

        setAdminAccess(nextAdminAccess)
        setLoadState('ready')
      } catch (requestError) {
        if (ignore) {
          return
        }

        setAdminAccess(null)
        setError(requestError)
        setLoadState('error')
      }
    }

    loadAdminAccess()

    return () => {
      ignore = true
    }
  }, [appUser, currentUser, enabled, isAuthLoading, reloadKey])

  return {
    adminAccess,
    error,
    hasPermission: (permission) => hasAdminPermission(adminAccess, permission),
    isLoading: isAuthLoading || isWaitingToLoad,
    loadState,
  }
}
