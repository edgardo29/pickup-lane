import { useCallback, useEffect, useState } from 'react'
import {
  onAuthStateChanged,
  signOut,
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

  const loadExistingAppUser = useCallback(async (user) => {
    setFirebaseUser(user)
    setAppUser(null)
    setStatus('loading')

    try {
      const existingUser = await getAuthenticatedAppUser(user)
      setAppUser(existingUser)
      setStatus('ready')
      return existingUser
    } catch (error) {
      if (!isMissingAppUserError(error)) {
        throw error
      }

      setAppUser(null)
      setStatus('ready')
      return null
    }
  }, [])

  const syncAndStoreUser = useCallback(async (user) => {
    setFirebaseUser(user)
    setStatus('loading')

    const syncedUser = await syncFirebaseUser(user)
    setPendingGoogleSignup(false)
    setPendingSignup(null)
    setAppUser(syncedUser)
    setStatus('ready')
    return syncedUser
  }, [])

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (!user) {
        setFirebaseUser(null)
        setAppUser(null)
        setPendingGoogleSignup(false)
        setStatus('ready')
        return
      }

      loadExistingAppUser(user)
        .catch(async (error) => {
          setAppUser(null)

          if (isMissingAppUserError(error)) {
            await signOut(auth).catch(() => {})
            setFirebaseUser(null)
          }
        })
        .finally(() => {
          setStatus('ready')
        })
    }, async (error) => {
      setFirebaseUser(null)
      setAppUser(null)
      setPendingGoogleSignup(false)
      setStatus('ready')

      if (isMissingAppUserError(error)) {
        await signOut(auth).catch(() => {})
      }
    })

    return unsubscribe
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
