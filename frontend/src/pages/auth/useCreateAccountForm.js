import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { checkEmailAvailability } from '../../lib/authApi.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import { useCleanupUnfinishedSignupOnEntry, useGoogleRedirectCompletion } from '../../features/auth/authHooks.js'
import {
  getPostAuthPath,
  getSafeAuthBackPath,
  isValidEmail,
  isValidPassword,
} from '../../features/auth/authHelpers.js'

export function useCreateAccountForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    appUser,
    beginEmailSignup,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    settleGoogleSignupRedirect,
    signInWithGoogle,
  } = useAuth()
  const [email, setEmail] = useState(pendingSignup?.email ?? '')
  const [password, setPassword] = useState(pendingSignup?.password ?? '')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const returnPath = typeof location.state?.from === 'string' ? location.state.from : ''
  const backPath = typeof location.state?.backTo === 'string'
    ? location.state.backTo
    : getSafeAuthBackPath(returnPath)

  useCleanupUnfinishedSignupOnEntry({
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    setError,
  })

  useGoogleRedirectCompletion({
    appUser,
    currentUser,
    isLoading,
    navigate,
    pendingGoogleSignup,
    settleGoogleSignupRedirect,
  })

  async function handleCreateAccount(event) {
    event.preventDefault()
    setStatus('submitting')
    setError('')

    const trimmedEmail = email.trim()

    if (!isValidEmail(trimmedEmail)) {
      setError('Enter a valid email.')
      setStatus('idle')
      return
    }

    if (!password) {
      setError('Create a password.')
      setStatus('idle')
      return
    }

    if (!isValidPassword(password)) {
      setError('Password must be at least 8 characters and include a number or symbol.')
      setStatus('idle')
      return
    }

    try {
      const availability = await checkEmailAvailability(trimmedEmail)

      if (!availability.available) {
        setError('An account already exists with this email.')
        setStatus('idle')
        return
      }

      beginEmailSignup({ email: trimmedEmail.toLowerCase(), password })
      setStatus('idle')
      navigate('/finish-profile', { state: { from: returnPath } })
    } catch {
      setError('Could not check this email. Please try again.')
      setStatus('idle')
    }
  }

  async function handleGoogleSignIn() {
    setStatus('submitting')
    setError('')

    try {
      const signedInUser = await signInWithGoogle()
      if (signedInUser) {
        navigate(returnPath || getPostAuthPath(signedInUser))
      } else {
        navigate('/finish-profile', { state: { from: returnPath } })
      }
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return {
    email,
    backPath,
    error,
    handleCreateAccount,
    handleGoogleSignIn,
    isSubmitting: status === 'submitting',
    password,
    returnPath,
    setEmail,
    setPassword,
    setShowPassword,
    showPassword,
  }
}
