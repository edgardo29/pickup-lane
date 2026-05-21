import {
  EmailAuthProvider,
  confirmPasswordReset as confirmFirebasePasswordReset,
  createUserWithEmailAndPassword,
  linkWithCredential,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  verifyPasswordResetCode,
} from 'firebase/auth'
import { auth } from '../lib/firebase.js'

export function buildAuthProviderCredentialActions({
  firebaseUser,
  loadExistingAppUser,
  setFirebaseUser,
  setPendingGoogleSignup,
  setPendingSignup,
  syncAndStoreUser,
}) {
  return {
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
      await confirmFirebasePasswordReset(auth, code, password)
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
    signUpWithEmail: async (email, password) => {
      const credential = await createUserWithEmailAndPassword(auth, email, password)
      const syncedUser = await syncAndStoreUser(credential.user)
      setPendingSignup(null)
      return syncedUser
    },
  }
}
