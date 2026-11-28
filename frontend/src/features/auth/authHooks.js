import { useEffect, useState } from 'react'
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
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState(null)
  const uid = currentUser?.uid
  const needed = !disabled && !isLoading && Boolean(currentUser)
    && !appUser?.id && !pendingGoogleSignup && !pendingSignup
  const settled = result && result.uid === uid && result.attempt === attempt ? result : null

  useEffect(() => {
    if (!needed) return undefined
    let ignore = false
    cleanupUnfinishedSignup().then(() => {
      if (!ignore) setResult({ uid, attempt, failed: false })
    }).catch(() => {
      if (!ignore) {
        setResult({ uid, attempt, failed: true })
        setError('Could not cancel sign-up. Please try again.')
      }
    })
    return () => { ignore = true }
  }, [attempt, cleanupUnfinishedSignup, needed, setError, uid])

  return {
    cleanupFailed: Boolean(settled?.failed),
    isCleaning: needed && !settled,
    retryCleanup: () => { setError(''); setAttempt((value) => value + 1) },
  }
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
