import {
  useCallback,
  useMemo,
  useState,
} from 'react'
import { useAuth } from '../../../hooks/useAuth.js'
import {
  AdminAccessContext,
  useAdminAccessState,
} from './useAdminAccess.js'

function AdminAccessProvider({ children }) {
  const { appUser } = useAuth()
  const [reloadKey, setReloadKey] = useState(0)
  const accessState = useAdminAccessState({
    enabled: Boolean(appUser),
    reloadKey,
  })
  const reload = useCallback(() => {
    setReloadKey((current) => current + 1)
  }, [])
  const value = useMemo(
    () => ({
      ...accessState,
      reload,
    }),
    [accessState, reload],
  )

  return (
    <AdminAccessContext.Provider value={value}>
      {children}
    </AdminAccessContext.Provider>
  )
}

export default AdminAccessProvider
