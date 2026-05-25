import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { isValidEmail } from '../../../features/auth/authHelpers.js'
import { useAuth } from '../../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../../lib/authErrors.js'

const ADMIN_ACCESS_ERROR = 'This account does not have admin access.'
const DEFAULT_ADMIN_PATH = '/admin/official-games'

function getAdminReturnPath(from) {
  if (typeof from !== 'string') {
    return DEFAULT_ADMIN_PATH
  }

  if (!from.startsWith('/admin') || from.startsWith('/admin/sign-in')) {
    return DEFAULT_ADMIN_PATH
  }

  return from
}

export function useAdminSignInForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const { appUser, isLoading, logout, signInWithEmail } = useAuth()
  const returnPath = getAdminReturnPath(location.state?.from)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [formError, setFormError] = useState(
    location.state?.adminDenied ? ADMIN_ACCESS_ERROR : '',
  )
  const isSignedInNonAdmin = !isLoading && Boolean(appUser) && appUser.role !== 'admin'
  const error = isSignedInNonAdmin ? ADMIN_ACCESS_ERROR : formError

  useEffect(() => {
    if (isLoading || !appUser) {
      return
    }

    if (appUser.role === 'admin') {
      navigate(returnPath, { replace: true })
      return
    }
  }, [appUser, isLoading, navigate, returnPath])

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

    try {
      const signedInUser = await signInWithEmail(trimmedEmail, password)

      if (signedInUser?.role !== 'admin') {
        await logout().catch(() => null)
        setFormError(ADMIN_ACCESS_ERROR)
        setStatus('idle')
        return
      }

      navigate(returnPath, { replace: true })
    } catch (requestError) {
      setFormError(getAuthErrorMessage(requestError))
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
