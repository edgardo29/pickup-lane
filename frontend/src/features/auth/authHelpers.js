import { getAuthErrorMessage } from '../../lib/authErrors.js'
import { minimumSignupAge } from './authConstants.js'

export function getPostAuthPath(user) {
  return getPostAuthNavigation(user).to
}

// Marks an arrival at the saved destination straight from sign-in, so a page
// whose content is no longer available can send the visitor to game discovery.
export function getAuthReturnState(returnPath) {
  return returnPath ? { authReturn: true } : undefined
}

// Where a visitor goes once signed in. An unfinished profile goes to Finish
// Profile first, carrying the saved destination; a finished one goes to the
// destination, or to game discovery when there is none.
export function getPostAuthNavigation(user, returnPath) {
  if (user?.account_status === 'suspended') {
    return { to: '/account-suspended' }
  }

  returnPath = getSafeAuthReturnPath(returnPath)
  if (!hasCompleteProfile(user)) {
    return { to: '/finish-profile', state: returnPath ? { from: returnPath } : undefined }
  }

  return { to: returnPath || '/games', state: getAuthReturnState(returnPath) }
}

// Only registered player routes can be authentication destinations. Keep the
// query intact: checkout intent and the selected list tab live there.
export function getSafeAuthReturnPath(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\s#%]/.test(value.split('?')[0]) || /[\\\r\n]/.test(value)) return ''
  const pathname = value.split('?')[0]
  const pages = ['/', '/games', '/games/browse', '/need-a-sub', '/player-hub', '/create-game', '/my-games', '/inbox', '/profile', '/profile/edit', '/profile/payment-methods', '/settings', '/settings/payment-methods', '/terms', '/privacy', '/policies/cancellation-refunds']
  const id = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
  const record = new RegExp(`^/(games/${id}(/checkout|/edit)?|need-a-sub/posts/${id}(/edit|/published|/manage)?)$`)
  return pages.includes(pathname) || record.test(pathname) ? value : ''
}

export function getSafeAuthBackPath(returnPath, fallback = '/') {
  if (!returnPath || typeof returnPath !== 'string') {
    return fallback
  }

  if (!returnPath.startsWith('/') || returnPath.startsWith('//')) {
    return fallback
  }

  const [pathname] = returnPath.split('?')

  if (pathname === '/' || pathname === '/games' || pathname === '/need-a-sub') {
    return pathname
  }

  if (pathname.startsWith('/games/') && pathname.endsWith('/checkout')) {
    return pathname.replace(/\/checkout$/, '')
  }

  if (pathname.startsWith('/games/') && pathname.endsWith('/edit')) {
    return pathname.replace(/\/edit$/, '')
  }

  if (pathname.startsWith('/games/')) {
    return pathname
  }

  if (pathname.startsWith('/need-a-sub/posts/') && pathname.endsWith('/edit')) {
    return pathname.replace(/\/edit$/, '')
  }

  if (pathname.startsWith('/need-a-sub/posts/')) {
    return pathname
  }

  return fallback
}

export function hasCompleteProfile(user) {
  return Boolean(
    user?.first_name?.trim?.() &&
      user?.last_name?.trim?.() &&
      user?.date_of_birth,
  )
}

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

export function isValidPassword(value) {
  return value.length >= 8 && /[\d\W_]/.test(value)
}

export function getPasswordResetLinkError(error) {
  const normalized = `${error?.code || ''} ${error?.message || ''}`.toLowerCase()

  if (normalized.includes('expired-action-code')) {
    return 'This reset link expired. Send a new reset email.'
  }

  if (normalized.includes('invalid-action-code')) {
    return 'This reset link is invalid or has already been used.'
  }

  if (normalized.includes('weak-password')) {
    return 'Password must be at least 8 characters and include a number or symbol.'
  }

  return getAuthErrorMessage(error)
}

export function splitIsoDate(dateString) {
  if (!dateString || !/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
    return { day: '', month: '', year: '' }
  }

  const [year, month, day] = dateString.split('-')
  return { day, month, year }
}

export function splitDisplayName(displayName) {
  const parts = displayName?.trim().split(/\s+/).filter(Boolean) ?? []

  if (parts.length === 0) {
    return { firstName: '', lastName: '' }
  }

  if (parts.length === 1) {
    return { firstName: parts[0], lastName: '' }
  }

  return {
    firstName: parts[0],
    lastName: parts.slice(1).join(' '),
  }
}

export function getBirthdayValidation(month, day, year) {
  if (!month || !day || !year) return { isValid: false, message: 'Enter your birthday.' }
  const value = `${year}-${month}-${day}`
  const dateOfBirth = new Date(`${value}T00:00:00Z`)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || Number.isNaN(dateOfBirth.getTime())
    || dateOfBirth.toISOString().slice(0, 10) !== value) {
    return { isValid: false, message: 'Enter a valid birthday.' }
  }
  // Signup uses Chicago's calendar even when the device is elsewhere.
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date()).map(({ type, value }) => [type, value]))
  const today = `${parts.year}-${parts.month}-${parts.day}`
  if (value > today) return { isValid: false, message: 'Birthday cannot be in the future.' }
  const eighteenthBirthday = new Date(dateOfBirth)
  // setUTCFullYear moves February 29 to March 1 in a non-leap year.
  eighteenthBirthday.setUTCFullYear(eighteenthBirthday.getUTCFullYear() + minimumSignupAge)
  if (eighteenthBirthday.toISOString().slice(0, 10) > today) {
    return { isValid: false, message: `You must be at least ${minimumSignupAge} years old to use Pickup Lane.` }
  }
  return { isValid: true, value }
}

export function getBirthYearOptions() {
  const currentYear = new Date().getFullYear()

  return Array.from({ length: 101 }, (_, index) => String(currentYear - index))
}

export function getDaysInMonth(month, year) {
  const monthNumber = Number(month)

  if (!monthNumber) {
    return 31
  }

  const yearNumber = Number(year) || 2000
  return new Date(yearNumber, monthNumber, 0).getDate()
}

export function pad2(value) {
  return String(value).padStart(2, '0')
}
