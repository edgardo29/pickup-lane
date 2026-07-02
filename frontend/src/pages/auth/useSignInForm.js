import { useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import { useGoogleRedirectCompletion } from '../../features/auth/authHooks.js'
import { getPostAuthPath, isValidEmail } from '../../features/auth/authHelpers.js'

export function useSignInForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const {
    appUser,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    settleGoogleSignupRedirect,
    signInWithEmail,
    signInWithGoogle,
  } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const resetStatus = searchParams.get('reset')
  const returnPath = typeof location.state?.from === 'string' ? location.state.from : ''

  useGoogleRedirectCompletion({
    appUser,
    currentUser,
    isLoading,
    navigate,
    pendingGoogleSignup,
    settleGoogleSignupRedirect,
  })

  async function handleEmailSignIn(event) {
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
      setError('Enter your password.')
      setStatus('idle')
      return
    }

    try {
      const signedInUser = await signInWithEmail(trimmedEmail, password)
      navigate(returnPath || getPostAuthPath(signedInUser), { replace: true })
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  async function handleGoogleSignIn() {
    setStatus('submitting')
    setError('')

    try {
      const signedInUser = await signInWithGoogle()
      if (signedInUser) {
        navigate(returnPath || getPostAuthPath(signedInUser), { replace: true })
      } else {
        navigate('/finish-profile', { replace: true, state: { from: returnPath } })
      }
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return {
    email,
    error,
    handleEmailSignIn,
    handleGoogleSignIn,
    isSubmitting: status === 'submitting',
    password,
    resetStatus,
    returnPath,
    setEmail,
    setPassword,
    setShowPassword,
    showPassword,
  }
}
