import { useEffect } from 'react'
import { getPostAuthPath } from './authHelpers.js'

export function useCleanupUnfinishedSignupOnEntry({
  appUser,
  cleanupUnfinishedSignup,
  currentUser,
  isLoading,
  pendingGoogleSignup,
  pendingSignup,
  setError,
}) {
  useEffect(() => {
    let ignore = false

    async function cleanup() {
      if (
        isLoading ||
        !currentUser ||
        appUser?.id ||
        pendingGoogleSignup ||
        pendingSignup
      ) {
        return
      }

      try {
        await cleanupUnfinishedSignup()
      } catch {
        if (!ignore) {
          setError('Could not reset the previous sign-up. Please try again.')
        }
      }
    }

    cleanup()

    return () => {
      ignore = true
    }
  }, [
    appUser?.id,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    setError,
  ])
}

export function useGoogleRedirectCompletion({
  appUser,
  currentUser,
  isLoading,
  navigate,
  pendingGoogleSignup,
  settleGoogleSignupRedirect,
}) {
  useEffect(() => {
    if (isLoading) {
      return
    }

    if (appUser) {
      settleGoogleSignupRedirect()
      navigate(getPostAuthPath(appUser), { replace: true })
      return
    }

    if (currentUser && pendingGoogleSignup) {
      navigate('/finish-profile')
    }
  }, [
    appUser,
    currentUser,
    isLoading,
    navigate,
    pendingGoogleSignup,
    settleGoogleSignupRedirect,
  ])
}
