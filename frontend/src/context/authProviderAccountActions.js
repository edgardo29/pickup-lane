import { signOut } from 'firebase/auth'
import { auth } from '../lib/firebase.js'
import {
  cleanupUnfinishedAccount,
  deleteAuthenticatedAccount,
} from '../lib/authApi.js'
import { isMissingAppUserError } from './authProviderHelpers.js'

export function buildAuthProviderAccountActions({
  firebaseUser,
  setAppUser,
  setFirebaseUser,
  setPendingGoogleSignup,
  setPendingSignup,
}) {
  return {
    cleanupUnfinishedSignup: async () => {
      if (!firebaseUser) {
        setPendingGoogleSignup(false)
        setPendingSignup(null)
        return
      }

      if (auth.currentUser?.uid !== firebaseUser.uid) {
        throw new Error('The signed-in account changed.')
      }
      // Keep the session and draft available when Firebase cleanup fails.
      await cleanupUnfinishedAccount(firebaseUser)
      if (auth.currentUser?.uid !== firebaseUser.uid) return
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
  }
}
