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
    sendCurrentUserVerificationEmail: async () => {
      const activeUser = firebaseUser || await waitForCurrentFirebaseUser()

      if (!activeUser) {
        throw new Error('Sign in before verifying your email.')
      }

      await activeUser.reload()
      const latestUser = auth.currentUser || activeUser
      if (latestUser.emailVerified) {
        const syncedUser = await syncFirebaseUser(latestUser, true)
        setFirebaseUser(latestUser)
        setAppUser(syncedUser)
        return
      }

      await sendEmailVerification(activeUser, {
        url: `${window.location.origin}/create-game`,
        handleCodeInApp: false,
      })
    },
    refreshCurrentUserVerification: async () => {
      const activeUser = firebaseUser || await waitForCurrentFirebaseUser()

      if (!activeUser) {
        return null
      }

      await activeUser.reload()
      const refreshedUser = auth.currentUser || activeUser
      setFirebaseUser(refreshedUser)

      if (!refreshedUser) {
        return null
      }

      const refreshedAppUser = refreshedUser.emailVerified
        ? await syncFirebaseUser(refreshedUser, true)
        : await getAuthenticatedAppUser(refreshedUser, true)
      setAppUser((currentAppUser) => {
        if (
          currentAppUser?.id === refreshedAppUser?.id &&
          currentAppUser?.email_verified_at === refreshedAppUser?.email_verified_at
        ) {
          return currentAppUser
        }

        return refreshedAppUser
      })
      return refreshedAppUser
    },
  }
}
