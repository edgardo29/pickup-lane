import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  EmailAuthProvider,
  GoogleAuthProvider,
  confirmPasswordReset,
  createUserWithEmailAndPassword,
  linkWithCredential,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  verifyPasswordResetCode,
} from 'firebase/auth'
import { auth } from '../lib/firebase.js'
import {
  cleanupUnfinishedAccount,
  deleteAuthenticatedAccount,
  getAuthenticatedAppUser,
  syncFirebaseUser,
} from '../lib/authApi.js'
import { AuthContext } from './authContext.js'

const googleProvider = new GoogleAuthProvider()

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

  const value = useMemo(
    () => ({
      appUser,
      currentUser: firebaseUser,
      isAuthenticated: Boolean(appUser),
      isLoading: status === 'loading',
      beginEmailSignup: (signupData) => {
        setPendingSignup(signupData)
      },
      clearPendingSignup: () => {
        setPendingSignup(null)
      },
      cleanupUnfinishedSignup: async () => {
        if (!firebaseUser) {
          setPendingGoogleSignup(false)
          setPendingSignup(null)
          return
        }

        await cleanupUnfinishedAccount(firebaseUser)
        await signOut(auth).catch(() => {})
        setFirebaseUser(null)
        setAppUser(null)
        setPendingSignup(null)
        setPendingGoogleSignup(false)
      },
      deleteAccount: async (confirmation) => {
        try {
          await deleteAuthenticatedAccount(firebaseUser, confirmation)
        } catch (error) {
          if (isMissingAppUserError(error)) {
            return
          }

          throw error
        }
      },
      logout: async () => {
        await signOut(auth)
        setFirebaseUser(null)
        setAppUser(null)
        setPendingSignup(null)
        setPendingGoogleSignup(false)
      },
      sendPasswordReset: async (email) => {
        await sendPasswordResetEmail(auth, email, {
          url: `${window.location.origin}/reset-password`,
          handleCodeInApp: true,
        })
      },
      verifyPasswordReset: async (code) => {
        return verifyPasswordResetCode(auth, code)
      },
      confirmPasswordReset: async (code, password) => {
        await confirmPasswordReset(auth, code, password)
      },
      addPasswordToCurrentAccount: async (password) => {
        if (!firebaseUser?.email) {
          throw new Error('Sign in before adding a password.')
        }

        const credential = EmailAuthProvider.credential(firebaseUser.email, password)
        await linkWithCredential(firebaseUser, credential)
        await firebaseUser.reload()
        setFirebaseUser(auth.currentUser)
      },
      signInWithEmail: async (email, password) => {
        const credential = await signInWithEmailAndPassword(auth, email, password)
        const existingUser = await loadExistingAppUser(credential.user)
        setPendingSignup(null)
        setPendingGoogleSignup(false)
        return existingUser
      },
      signInWithGoogle: async () => {
        setPendingGoogleSignup(true)

        try {
          const credential = await signInWithPopup(auth, googleProvider)
          const existingUser = await loadExistingAppUser(credential.user)

          if (existingUser && hasCompleteProfile(existingUser)) {
            setPendingGoogleSignup(false)
          }

          setPendingSignup(null)
          return existingUser
        } catch (error) {
          setPendingGoogleSignup(false)
          throw error
        }
      },
      settleGoogleSignupRedirect: () => {
        setPendingGoogleSignup(false)
      },
      signUpWithEmail: async (email, password) => {
        const credential = await createUserWithEmailAndPassword(auth, email, password)
        const syncedUser = await syncAndStoreUser(credential.user)
        setPendingSignup(null)
        return syncedUser
      },
      syncCurrentFirebaseUser: async () => {
        if (!firebaseUser) {
          return null
        }

        return syncAndStoreUser(firebaseUser)
      },
      pendingSignup,
      pendingGoogleSignup,
      updateAppUser: setAppUser,
    }),
    [
      appUser,
      firebaseUser,
      loadExistingAppUser,
      pendingGoogleSignup,
      pendingSignup,
      status,
      syncAndStoreUser,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function isMissingAppUserError(error) {
  const code = error?.code || ''
  const message = error?.message || ''

  return (
    code.includes('user-not-found') ||
    message.includes('USER_NOT_FOUND') ||
    message.toLowerCase().includes('user not found')
  )
}

function hasCompleteProfile(user) {
  return Boolean(user?.first_name && user?.last_name && user?.date_of_birth)
}
