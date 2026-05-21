import { useCallback, useEffect, useState } from 'react'
import {
  clearEmailVerificationCooldown,
  getEmailVerificationCooldown,
  getEmailVerificationErrorMessage,
  getRemainingCooldownSeconds,
  setEmailVerificationCooldown,
} from './createGameVerification.js'

export function useCreateGameEmailVerification({
  appUser,
  isEditMode,
  refreshCurrentUserVerification,
  sendCurrentUserVerificationEmail,
}) {
  const [verificationError, setVerificationError] = useState('')
  const [verificationNotice, setVerificationNotice] = useState('')
  const [verificationStatus, setVerificationStatus] = useState('idle')
  const [verificationCooldownUntil, setVerificationCooldownUntil] = useState(0)
  const [verificationCooldownSeconds, setVerificationCooldownSeconds] = useState(0)
  const shouldWatchForVerification = Boolean(appUser?.id && !isEditMode && !appUser.email_verified_at)

  const resetVerificationState = useCallback((userId) => {
    clearEmailVerificationCooldown(userId)
    setVerificationCooldownUntil(0)
    setVerificationCooldownSeconds(0)
    setVerificationError('')
    setVerificationNotice('')
    setVerificationStatus('idle')
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (!appUser?.id || appUser.email_verified_at) {
        if (appUser?.id) {
          clearEmailVerificationCooldown(appUser.id)
        }
        setVerificationCooldownUntil(0)
        setVerificationCooldownSeconds(0)
        return
      }

      const storedCooldownUntil = getEmailVerificationCooldown(appUser.id)
      setVerificationCooldownUntil(storedCooldownUntil)
      setVerificationCooldownSeconds(getRemainingCooldownSeconds(storedCooldownUntil))
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [appUser?.email_verified_at, appUser?.id])

  useEffect(() => {
    if (!shouldWatchForVerification) {
      return undefined
    }

    async function refreshIfVerified() {
      const refreshedAppUser = await refreshCurrentUserVerification().catch(() => null)

      if (!refreshedAppUser?.email_verified_at) {
        return
      }

      resetVerificationState(refreshedAppUser.id)
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        refreshIfVerified()
      }
    }

    window.addEventListener('focus', refreshIfVerified)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('focus', refreshIfVerified)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [refreshCurrentUserVerification, resetVerificationState, shouldWatchForVerification])

  useEffect(() => {
    if (verificationCooldownUntil <= Date.now()) {
      const timeoutId = window.setTimeout(() => {
        setVerificationCooldownSeconds(0)
      }, 0)

      return () => window.clearTimeout(timeoutId)
    }

    const timeoutId = window.setTimeout(() => {
      setVerificationCooldownSeconds(getRemainingCooldownSeconds(verificationCooldownUntil))
    }, 0)

    const intervalId = window.setInterval(() => {
      const remainingSeconds = getRemainingCooldownSeconds(verificationCooldownUntil)
      setVerificationCooldownSeconds(remainingSeconds)

      if (remainingSeconds <= 0) {
        window.clearInterval(intervalId)
      }
    }, 1000)

    return () => {
      window.clearTimeout(timeoutId)
      window.clearInterval(intervalId)
    }
  }, [verificationCooldownUntil])

  async function sendEmailVerificationLink() {
    const activeUserId = appUser?.id
    const storedCooldownUntil = getEmailVerificationCooldown(activeUserId)
    const storedCooldownSeconds = getRemainingCooldownSeconds(storedCooldownUntil)

    if (verificationCooldownSeconds > 0 || storedCooldownSeconds > 0) {
      if (storedCooldownSeconds > 0) {
        setVerificationCooldownUntil(storedCooldownUntil)
        setVerificationCooldownSeconds(storedCooldownSeconds)
      }
      return
    }

    setVerificationError('')
    setVerificationNotice('')
    setVerificationStatus('sending')

    try {
      await sendCurrentUserVerificationEmail()
      setVerificationStatus('sent')
      startEmailVerificationCooldown(activeUserId, 60)
    } catch (error) {
      const verificationMessage = getEmailVerificationErrorMessage(error)
      setVerificationError(verificationMessage.message)
      if (verificationMessage.cooldownSeconds > 0) {
        startEmailVerificationCooldown(activeUserId, verificationMessage.cooldownSeconds)
      }
      setVerificationStatus('idle')
    }
  }

  function startEmailVerificationCooldown(userId, seconds) {
    const cooldownUntil = Date.now() + seconds * 1000

    setEmailVerificationCooldown(userId, cooldownUntil)
    setVerificationCooldownUntil(cooldownUntil)
    setVerificationCooldownSeconds(seconds)
  }

  return {
    resetVerificationState,
    sendEmailVerificationLink,
    verificationCooldownSeconds,
    verificationError,
    verificationNotice,
    verificationStatus,
  }
}
