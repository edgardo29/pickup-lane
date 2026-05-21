export function clearEmailVerificationCooldown(userId) {
  if (!userId) {
    return
  }

  try {
    window.localStorage.removeItem(getEmailVerificationCooldownKey(userId))
  } catch {
    // Ignore private browsing/storage failures.
  }
}

export function getEmailVerificationCooldown(userId) {
  if (!userId) {
    return 0
  }

  try {
    const storedValue = window.localStorage.getItem(getEmailVerificationCooldownKey(userId))
    const cooldownUntil = Number(storedValue)

    return Number.isFinite(cooldownUntil) && cooldownUntil > Date.now() ? cooldownUntil : 0
  } catch {
    return 0
  }
}

export function getEmailVerificationErrorMessage(error) {
  const code = error?.code || ''
  const message = error?.message || ''
  const normalizedError = `${code} ${message}`.toLowerCase()

  if (normalizedError.includes('too-many-requests')) {
    return {
      cooldownSeconds: 300,
      message: 'Too many verification emails were sent. Try again in a few minutes.',
    }
  }

  if (normalizedError.includes('network-request-failed') || normalizedError.includes('failed to fetch')) {
    return {
      cooldownSeconds: 0,
      message: 'Network issue. Check your connection and try again.',
    }
  }

  if (normalizedError.includes('requires-recent-login')) {
    return {
      cooldownSeconds: 0,
      message: 'Sign in again, then resend the verification email.',
    }
  }

  return {
    cooldownSeconds: 0,
    message: 'Unable to send verification email right now. Please try again in a minute.',
  }
}

export function getRemainingCooldownSeconds(cooldownUntil) {
  return Math.max(Math.ceil((cooldownUntil - Date.now()) / 1000), 0)
}

export function setEmailVerificationCooldown(userId, cooldownUntil) {
  if (!userId) {
    return
  }

  try {
    window.localStorage.setItem(
      getEmailVerificationCooldownKey(userId),
      String(cooldownUntil),
    )
  } catch {
    // Local storage is best-effort; Firebase still enforces the real limit.
  }
}

function getEmailVerificationCooldownKey(userId) {
  return `pickup-lane:email-verification-cooldown:${userId}`
}
