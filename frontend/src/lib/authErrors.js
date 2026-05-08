export function getAuthErrorMessage(error) {
  const code = error?.code || ''
  const message = error?.message || ''
  const normalized = `${code} ${message}`.toLowerCase()

  if (normalized.includes('invalid-email')) {
    return 'Enter a valid email.'
  }

  if (
    normalized.includes('invalid-credential') ||
    normalized.includes('wrong-password')
  ) {
    return 'Email or password is incorrect.'
  }

  if (normalized.includes('email-already-in-use')) {
    return 'An account already exists with this email.'
  }

  if (normalized.includes('weak-password')) {
    return 'Password must be at least 8 characters and include a number or symbol.'
  }

  if (normalized.includes('popup-closed-by-user')) {
    return 'Sign-in was cancelled before it finished.'
  }

  if (normalized.includes('provider-already-linked')) {
    return 'Password sign-in is already enabled for this account.'
  }

  if (normalized.includes('credential-already-in-use')) {
    return 'This sign-in method is already connected to another account.'
  }

  if (normalized.includes('requires-recent-login')) {
    return 'Sign in again, then try this one more time.'
  }

  if (normalized.includes('network-request-failed') || normalized.includes('failed to fetch')) {
    return 'Network issue. Check your connection and try again.'
  }

  if (normalized.includes('user-not-found')) {
    return 'No account was found with that email.'
  }

  return 'Something went wrong. Please try again.'
}
