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

      let cleanupError = null

      try {
        await cleanupUnfinishedAccount(firebaseUser)
      } catch (error) {
        cleanupError = error
      }

      await signOut(auth).catch(() => {})
      setFirebaseUser(null)
      setAppUser(null)
      setPendingSignup(null)
      setPendingGoogleSignup(false)

      if (cleanupError) {
        throw cleanupError
      }
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
