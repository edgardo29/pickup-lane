import { verificationReturnLink } from '../features/email-verification/emailVerificationReturn.js'
import { sendEmailVerification } from 'firebase/auth'
import {
  getAuthenticatedAppUser,
  syncFirebaseUser,
} from '../lib/authApi.js'
import { auth } from '../lib/firebase.js'
import { waitForCurrentFirebaseUser } from './authProviderHelpers.js'

export function buildAuthProviderVerificationActions({
  firebaseUser,
  setAppUser,
  setFirebaseUser,
}) {
  return {
    sendCurrentUserVerificationEmail: async (destination = '/create-game') => {
      const activeUser = auth.currentUser || firebaseUser || await waitForCurrentFirebaseUser()

      if (!activeUser) {
        throw new Error('Sign in before verifying your email.')
      }

      await activeUser.reload()
      if (auth.currentUser?.uid !== activeUser.uid) {
        throw new Error('The signed-in account changed. Return to your form and try again.')
      }
      const latestUser = auth.currentUser || activeUser
      if (latestUser.emailVerified) {
        const syncedUser = await syncFirebaseUser(latestUser, true)
        if (auth.currentUser?.uid !== activeUser.uid) return
        setFirebaseUser(latestUser)
        setAppUser(syncedUser)
        return
      }

      await sendEmailVerification(activeUser, {
        url: `${window.location.origin}${verificationReturnLink(destination)}`,
        handleCodeInApp: false,
      })
    },
    refreshCurrentUserVerification: async () => {
      const activeUser = auth.currentUser || firebaseUser || await waitForCurrentFirebaseUser()

      if (!activeUser) {
        return null
      }

      await activeUser.reload()
      if (auth.currentUser?.uid !== activeUser.uid) {
        throw new Error('The signed-in account changed. Return to your form and try again.')
      }
      const refreshedUser = auth.currentUser || activeUser
      setFirebaseUser(refreshedUser)

      if (!refreshedUser) {
        return null
      }

      const refreshedAppUser = refreshedUser.emailVerified
        ? await syncFirebaseUser(refreshedUser, true)
        : await getAuthenticatedAppUser(refreshedUser, true)
      if (auth.currentUser?.uid !== activeUser.uid) return null
      setAppUser((currentAppUser) => {
        if (
          currentAppUser?.id === refreshedAppUser?.id &&
          currentAppUser?.email_verified_at === refreshedAppUser?.email_verified_at &&
          currentAppUser?.hosting_status === refreshedAppUser?.hosting_status &&
          currentAppUser?.account_status === refreshedAppUser?.account_status
        ) {
          return currentAppUser
        }

        return refreshedAppUser
      })
      return refreshedAppUser
    },
  }
}
