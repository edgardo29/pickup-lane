import { getAuthErrorMessage } from '../../lib/authErrors.js'

export function getPostAuthPath(user) {
  return hasCompleteProfile(user) ? '/games' : '/finish-profile'
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
  if (!month || !day || !year) {
    return { isValid: false, message: 'Enter your birthday.' }
  }

  const value = `${year}-${month}-${day}`
  const dateOfBirth = new Date(`${value}T00:00:00`)

  if (Number.isNaN(dateOfBirth.getTime())) {
    return { isValid: false, message: 'Enter a valid birthday.' }
  }

  const today = new Date()
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate())

  if (dateOfBirth > todayStart) {
    return { isValid: false, message: 'Birthday cannot be in the future.' }
  }

  const thirteenthBirthday = new Date(dateOfBirth)
  thirteenthBirthday.setFullYear(thirteenthBirthday.getFullYear() + 13)

  if (thirteenthBirthday > todayStart) {
    return {
      isValid: false,
      message: 'You must be at least 13 years old to use Pickup Lane.',
    }
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
