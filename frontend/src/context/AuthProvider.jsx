import { useCallback, useEffect, useRef, useState } from 'react'
import {
  onAuthStateChanged,
} from 'firebase/auth'
import { auth } from '../lib/firebase.js'
import {
  getAuthenticatedAppUser,
  syncFirebaseUser,
} from '../lib/authApi.js'
import { AuthContext } from './authContext.js'
import { isMissingAppUserError } from './authProviderHelpers.js'
import { useAuthProviderValue } from './useAuthProviderValue.js'

export function AuthProvider({ children }) {
  const [firebaseUser, setFirebaseUser] = useState(null)
  const [appUser, setAppUser] = useState(null)
  const [pendingSignup, setPendingSignup] = useState(null)
  const [pendingGoogleSignup, setPendingGoogleSignup] = useState(false)
  const [status, setStatus] = useState('loading')

  const session = useRef({ uid: null, version: 0, pending: null })

  const loadExistingAppUser = useCallback((user) => {
    if (auth.currentUser?.uid !== user.uid) return Promise.reject(Object.assign(new Error('The signed-in account changed.'), { code: 'auth/session-changed' }))
    if (session.current.uid === user.uid && session.current.pending) return session.current.pending
    const version = ++session.current.version
    session.current.uid = user.uid
    setFirebaseUser(user)
    setAppUser(null)
    setStatus('loading')
    const isCurrent = () => session.current.version === version && auth.currentUser?.uid === user.uid
    const pending = (async () => {
      try {
        const existingUser = await getAuthenticatedAppUser(user)
        if (!isCurrent()) throw Object.assign(new Error('The signed-in account changed.'), { code: 'auth/session-changed' })
        setAppUser(existingUser)
        return existingUser
      } catch (error) {
        if (!isCurrent()) throw error
        if (!isMissingAppUserError(error)) throw error
        setAppUser(null)
        return null
      } finally {
        if (isCurrent()) {
          session.current.pending = null
          setStatus('ready')
        }
      }
    })()
    session.current.pending = pending
    return pending
  }, [])

  const syncAndStoreUser = useCallback(async (user) => {
    if (auth.currentUser?.uid !== user.uid) throw new Error('The signed-in account changed.')
    const version = ++session.current.version
    session.current.uid = user.uid
    session.current.pending = null
    setFirebaseUser(user)
    setStatus('loading')
    try {
      const syncedUser = await syncFirebaseUser(user)
      if (session.current.version !== version || auth.currentUser?.uid !== user.uid) throw new Error('The signed-in account changed.')
      setPendingGoogleSignup(false)
      setPendingSignup(null)
      setAppUser(syncedUser)
      return syncedUser
    } finally {
      if (session.current.version === version && auth.currentUser?.uid === user.uid) setStatus('ready')
    }
  }, [])

  useEffect(() => {
    function clearSession() {
      session.current = { uid: null, version: session.current.version + 1, pending: null }
      setFirebaseUser(null)
      setAppUser(null)
      setPendingSignup(null)
      setPendingGoogleSignup(false)
      setStatus('ready')
    }
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (!user) {
        clearSession()
        return
      }
      // The form reports failures from its own operation. A restored session
      // remains signed out of the app when its account could not be loaded.
      loadExistingAppUser(user).catch(() => {})
    }, clearSession)
    return () => {
      unsubscribe()
      session.current.version += 1
    }
  }, [loadExistingAppUser])

  const value = useAuthProviderValue({
    appUser,
    firebaseUser,
    loadExistingAppUser,
    pendingGoogleSignup,
    pendingSignup,
    setAppUser,
    setFirebaseUser,
    setPendingGoogleSignup,
    setPendingSignup,
    status,
    syncAndStoreUser,
  })

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
