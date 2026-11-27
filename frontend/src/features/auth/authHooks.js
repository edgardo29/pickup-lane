import { useEffect } from 'react'
import { getPostAuthNavigation } from './authHelpers.js'

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
  returnPath,
}) {
  useEffect(() => {
    if (isLoading) {
      return
    }

    if (appUser) {
      settleGoogleSignupRedirect()
      const next = getPostAuthNavigation(appUser, returnPath)
      navigate(next.to, { replace: true, state: next.state })
      return
    }

    if (currentUser && pendingGoogleSignup) {
      const next = getPostAuthNavigation(null, returnPath)
      navigate(next.to, { replace: true, state: next.state })
    }
  }, [
    appUser,
    currentUser,
    isLoading,
    navigate,
    pendingGoogleSignup,
    settleGoogleSignupRedirect,
    returnPath,
  ])
}
