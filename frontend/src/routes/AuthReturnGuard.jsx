import { useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { readAuthReturnResource } from '../features/auth/authReturnApi.js'
import { useAuth } from '../hooks/useAuth.js'

// Check saved record destinations before rendering their content. Ordinary
// visits retain each page's own unavailable state and recovery behavior.
export function AuthReturnGuard({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { appUser, currentUser, isLoading } = useAuth()
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState(null)
  const checking = Boolean(location.state?.authReturn)
  const key = `${location.key}:${currentUser?.uid}:${attempt}`

  useEffect(() => {
    if (!checking || isLoading || !currentUser) return undefined
    let ignore = false
    readAuthReturnResource(location.pathname, currentUser).then((record) => {
      if (ignore) return
      const ownerOnly = /\/(edit|manage)$/.test(location.pathname)
      const owner = record?.owner_user_id ?? record?.host_user_id
      const gameEdit = /^\/games\/[^/]+\/edit$/.test(location.pathname)
      const editableGame = record?.game_type === 'community' && record.publish_status === 'published' && record.game_status === 'active' && Date.parse(record.starts_at) > Date.now()
      const postEdit = /^\/need-a-sub\/posts\/[^/]+\/edit$/.test(location.pathname)
      const editablePost = record?.post_status === 'active' && Date.parse(record.starts_at) > Date.now()
      if ((ownerOnly && owner !== appUser?.id) || (gameEdit && !editableGame) || (postEdit && !editablePost)) {
        setResult({ key, state: 'unavailable' })
        return
      }
      // Remove only this marker, retaining any other route context.
      const state = { ...location.state }
      delete state.authReturn
      // Signing in does not establish that this visitor just published a post.
      const destination = location.pathname.replace(/^(\/need-a-sub\/posts\/[^/]+)\/published$/, '$1')
      navigate(`${destination}${location.search}`, { replace: true, state })
    }).catch((error) => {
      if (!ignore) setResult({ key, state: [401, 403, 404].includes(error?.status) ? 'unavailable' : 'error' })
    })
    return () => { ignore = true }
  }, [appUser?.id, checking, currentUser, isLoading, key, location.pathname, location.search, location.state, navigate])

  if (!checking) return children
  if (result?.key === key && result.state === 'unavailable') return <Navigate to="/games" replace />
  if (result?.key === key && result.state === 'error') {
    return <main><p role="alert">Could not open your destination. Check your connection and try again.</p><button type="button" onClick={() => setAttempt((value) => value + 1)}>Try again</button></main>
  }
  return <p role="status">Opening your destination...</p>
}
