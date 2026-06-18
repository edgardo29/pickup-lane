import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { isValidEmail } from '../../../features/auth/authHelpers.js'
import { useAuth } from '../../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../../lib/authErrors.js'
import { auth } from '../../../lib/firebase.js'
import { fetchAdminMe } from '../shared/adminApi.js'
import {
  canAccessAdminPath,
  getDefaultAdminPath,
} from '../shared/adminWorkspaceData.js'

const ADMIN_ACCESS_ERROR = 'This account does not have staff access.'

function getAdminReturnPath(from, adminAccess) {
  const defaultPath = getDefaultAdminPath(adminAccess)

  if (typeof from !== 'string') {
    return defaultPath
  }

  if (!from.startsWith('/admin') || from.startsWith('/admin/sign-in')) {
    return defaultPath
  }

  const pathname = from.split('?')[0].split('#')[0]

  return canAccessAdminPath(pathname, adminAccess) ? from : defaultPath
}

export function useAdminSignInForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const { appUser, currentUser, isLoading, logout, signInWithEmail } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [formError, setFormError] = useState(
    location.state?.adminDenied ? ADMIN_ACCESS_ERROR : '',
  )
  const error = formError

  useEffect(() => {
    if (isLoading || !appUser || !currentUser) {
      return
    }

    let ignore = false

    async function confirmAdminAccess() {
      setStatus('submitting')
      setFormError('')

      try {
        const adminAccess = await fetchAdminMe({ firebaseUser: currentUser })

        if (ignore) {
          return
        }

        navigate(getAdminReturnPath(location.state?.from, adminAccess), { replace: true })
      } catch {
        if (ignore) {
          return
        }

        setFormError(ADMIN_ACCESS_ERROR)
        setStatus('idle')
      }
    }

    confirmAdminAccess()

    return () => {
      ignore = true
    }
  }, [appUser, currentUser, isLoading, location.state?.from, navigate])

  async function handleEmailSignIn(event) {
    event.preventDefault()
    setStatus('submitting')
    setFormError('')

    const trimmedEmail = email.trim()

    if (!isValidEmail(trimmedEmail)) {
      setFormError('Enter a valid email.')
      setStatus('idle')
      return
    }

    if (!password) {
      setFormError('Enter your password.')
      setStatus('idle')
      return
    }

    let didSignIn = false

    try {
      await signInWithEmail(trimmedEmail, password)
      didSignIn = true
      const firebaseUser = auth.currentUser

      if (!firebaseUser) {
        throw new Error(ADMIN_ACCESS_ERROR)
      }

      const adminAccess = await fetchAdminMe({ firebaseUser })

      navigate(getAdminReturnPath(location.state?.from, adminAccess), { replace: true })
    } catch (requestError) {
      const isAccessError = (
        requestError?.status === 401
        || requestError?.status === 403
        || requestError?.message === ADMIN_ACCESS_ERROR
      )

      if (didSignIn || isAccessError) {
        await logout().catch(() => null)
      }

      setFormError(isAccessError ? ADMIN_ACCESS_ERROR : getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return {
    email,
    error,
    handleEmailSignIn,
    isSubmitting: status === 'submitting' || isLoading,
    password,
    setEmail,
    setPassword,
    setShowPassword,
    showPassword,
  }
}
