import { useMemo } from 'react'
import { buildAuthProviderAccountActions } from './authProviderAccountActions.js'
import { buildAuthProviderCredentialActions } from './authProviderCredentialActions.js'
import { buildAuthProviderGoogleActions } from './authProviderGoogleActions.js'
import { buildAuthProviderVerificationActions } from './authProviderVerificationActions.js'

export function useAuthProviderValue({
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
}) {
  return useMemo(
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
      ...buildAuthProviderAccountActions({
        firebaseUser,
        setAppUser,
        setFirebaseUser,
        setPendingGoogleSignup,
        setPendingSignup,
      }),
      ...buildAuthProviderCredentialActions({
        firebaseUser,
        loadExistingAppUser,
        setFirebaseUser,
        setPendingGoogleSignup,
        setPendingSignup,
        syncAndStoreUser,
      }),
      ...buildAuthProviderGoogleActions({
        loadExistingAppUser,
        setPendingGoogleSignup,
        setPendingSignup,
      }),
      ...buildAuthProviderVerificationActions({
        firebaseUser,
        setAppUser,
        setFirebaseUser,
      }),
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
      setAppUser,
      setFirebaseUser,
      setPendingGoogleSignup,
      setPendingSignup,
      status,
      syncAndStoreUser,
    ],
  )
}
