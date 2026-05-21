import {
  GoogleAuthProvider,
  signInWithPopup,
} from 'firebase/auth'
import { auth } from '../lib/firebase.js'
import { hasCompleteProfile } from './authProviderHelpers.js'

const googleProvider = new GoogleAuthProvider()

export function buildAuthProviderGoogleActions({
  loadExistingAppUser,
  setPendingGoogleSignup,
  setPendingSignup,
}) {
  return {
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
  }
}
