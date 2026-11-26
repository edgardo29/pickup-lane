import { useCallback, useEffect, useRef, useState } from 'react'
import {
  clearEmailVerificationCooldown,
  getEmailVerificationCooldown,
  getEmailVerificationErrorMessage,
  getRemainingCooldownSeconds,
  setEmailVerificationCooldown,
} from './emailVerificationCooldown.js'

function initialVerification(userId) {
  const cooldownUntil = getEmailVerificationCooldown(userId)
  return {
    owner: { userId }, error: '', notice: '', status: 'idle',
    cooldownUntil, cooldownSeconds: getRemainingCooldownSeconds(cooldownUntil),
  }
}

export function useEmailVerification({
  appUser,
  enabled = true,
  destination,
  refreshCurrentUserVerification,
  sendCurrentUserVerificationEmail,
}) {
  const userId = appUser?.id
  const sendingRef = useRef(null)
  const [verification, setVerification] = useState(() => initialVerification(userId))
  const { owner, cooldownUntil } = verification
  const shouldWatchForVerification = Boolean(userId && enabled && !appUser.email_verified_at)

  // Replace this hook's own state before rendering a different account. A new
  // owner object also distinguishes signing back into the same account later.
  if (owner.userId !== userId) {
    setVerification(initialVerification(userId))
  }

  const updateVerification = useCallback((requestOwner, changes) => {
    setVerification((current) => current.owner === requestOwner
      ? { ...current, ...changes } : current)
  }, [])

  const resetVerificationState = useCallback((verifiedUserId) => {
    clearEmailVerificationCooldown(verifiedUserId)
    setVerification((current) => current.owner.userId === verifiedUserId
      ? { ...current, cooldownUntil: 0, cooldownSeconds: 0, error: '', notice: '', status: 'idle' }
      : current)
  }, [])

  useEffect(() => {
    if (!userId || !appUser.email_verified_at) return undefined
    const timeoutId = window.setTimeout(() => resetVerificationState(userId), 0)
    return () => window.clearTimeout(timeoutId)
  }, [appUser?.email_verified_at, resetVerificationState, userId])

  useEffect(() => {
    if (!shouldWatchForVerification) return undefined
    let ignore = false
    async function refreshIfVerified() {
      const refreshed = await refreshCurrentUserVerification().catch(() => null)
      if (!ignore && refreshed?.email_verified_at && refreshed.id === owner.userId) {
        resetVerificationState(refreshed.id)
      }
    }
    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') refreshIfVerified()
    }
    window.addEventListener('focus', refreshIfVerified)
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      ignore = true
      window.removeEventListener('focus', refreshIfVerified)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [owner, refreshCurrentUserVerification, resetVerificationState, shouldWatchForVerification])

  useEffect(() => {
    function updateCountdown() {
      const seconds = getRemainingCooldownSeconds(cooldownUntil)
      updateVerification(owner, { cooldownSeconds: seconds })
      return seconds
    }
    const timeoutId = window.setTimeout(updateCountdown, 0)
    if (cooldownUntil <= Date.now()) {
      return () => window.clearTimeout(timeoutId)
    }
    const intervalId = window.setInterval(() => {
      if (updateCountdown() === 0) window.clearInterval(intervalId)
    }, 1000)
    return () => {
      window.clearTimeout(timeoutId)
      window.clearInterval(intervalId)
    }
  }, [cooldownUntil, owner, updateVerification])

  function startEmailVerificationCooldown(seconds) {
    const until = Date.now() + seconds * 1000
    setEmailVerificationCooldown(owner.userId, until)
    return { cooldownUntil: until, cooldownSeconds: seconds }
  }

  async function sendEmailVerificationLink() {
    if (!owner.userId || !enabled) return
    const storedUntil = getEmailVerificationCooldown(owner.userId)
    const storedSeconds = getRemainingCooldownSeconds(storedUntil)
    if (sendingRef.current?.owner === owner || verification.cooldownSeconds > 0 || storedSeconds > 0) {
      if (storedSeconds > 0) {
        updateVerification(owner, { cooldownUntil: storedUntil, cooldownSeconds: storedSeconds })
      }
      return
    }
    const request = { owner }
    sendingRef.current = request
    updateVerification(owner, { error: '', notice: '', status: 'sending' })
    try {
      await sendCurrentUserVerificationEmail(destination)
      updateVerification(owner, { status: 'sent', ...startEmailVerificationCooldown(60) })
    } catch (error) {
      const feedback = getEmailVerificationErrorMessage(error)
      updateVerification(owner, {
        status: 'idle', error: feedback.message,
        ...(feedback.cooldownSeconds > 0 ? startEmailVerificationCooldown(feedback.cooldownSeconds) : {}),
      })
    } finally {
      // An older account's completion must not clear a newer pending request.
      if (sendingRef.current === request) sendingRef.current = null
    }
  }

  return {
    resetVerificationState,
    sendEmailVerificationLink,
    verificationCooldownSeconds: verification.cooldownSeconds,
    verificationError: verification.error,
    verificationNotice: verification.notice,
    verificationStatus: verification.status,
  }
}
