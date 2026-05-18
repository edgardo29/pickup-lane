import { useEffect } from 'react'
import { getPostAuthPath } from './authHelpers.js'

export function useCleanupUnfinishedSignupOnEntry({
  appUser,
  cleanupUnfinishedSignup,
  currentUser,
  disabled = false,
  isLoading,
  pendingGoogleSignup,
  pendingSignup,
  setError,
}) {
  useEffect(() => {
    let ignore = false

    async function cleanup() {
      if (
        disabled ||
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
        // Local/dev Firebase Admin cleanup can fail even though a local sign-out
        // is enough to unblock the next sign-in attempt.
        if (!ignore) setError('')
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
    disabled,
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
