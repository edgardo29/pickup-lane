import { onAuthStateChanged } from 'firebase/auth'
import { auth } from '../lib/firebase.js'

export function isMissingAppUserError(error) {
  const code = error?.code || ''
  const message = error?.message || ''

  return (
    code.includes('user-not-found') ||
    message.includes('USER_NOT_FOUND') ||
    message.toLowerCase().includes('user not found')
  )
}

export function waitForCurrentFirebaseUser(timeoutMs = 5000) {
  if (auth.currentUser) {
    return Promise.resolve(auth.currentUser)
  }

  return new Promise((resolve) => {
    let settled = false
    let unsubscribe = () => {}

    const finish = (user) => {
      if (settled) {
        return
      }

      settled = true
      window.clearTimeout(timeoutId)
      unsubscribe()
      resolve(user || auth.currentUser || null)
    }

    const timeoutId = window.setTimeout(() => finish(auth.currentUser || null), timeoutMs)
    unsubscribe = onAuthStateChanged(auth, finish, () => finish(null))
  })
}

export function hasCompleteProfile(user) {
  return Boolean(user?.first_name && user?.last_name && user?.date_of_birth)
}
