import { useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import { useGoogleRedirectCompletion } from '../../features/auth/authHooks.js'
import {
  getPostAuthNavigation,
  getSafeAuthBackPath,
  isValidEmail,
} from '../../features/auth/authHelpers.js'

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
  const [invalidField, setInvalidField] = useState('')
  const pending = useRef(false)
  const resetStatus = searchParams.get('reset')
  const returnPath = typeof location.state?.from === 'string' ? location.state.from : ''
  const backPath = typeof location.state?.backTo === 'string'
    ? location.state.backTo
    : getSafeAuthBackPath(returnPath)

  useGoogleRedirectCompletion({
    appUser,
    currentUser,
    isLoading: isLoading || status === 'submitting',
    navigate,
    pendingGoogleSignup,
    settleGoogleSignupRedirect,
    returnPath,
  })

  async function handleEmailSignIn(event) {
    event.preventDefault()
    if (pending.current || isLoading) return
    setInvalidField('')
    setStatus('submitting')
    setError('')

    const trimmedEmail = email.trim()

    if (!isValidEmail(trimmedEmail)) {
      setInvalidField('email')
      setError('Enter a valid email.')
      setStatus('idle')
      return
    }

    if (!password) {
      setInvalidField('password')
      setError('Enter your password.')
      setStatus('idle')
      return
    }

    pending.current = true
    try {
      const signedInUser = await signInWithEmail(trimmedEmail, password)
      if (!signedInUser) {
        const next = getPostAuthNavigation(null, returnPath)
        navigate(next.to, { replace: true, state: next.state })
      } else setStatus('idle')
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    } finally {
      pending.current = false
    }
  }

  async function handleGoogleSignIn() {
    if (pending.current || isLoading) return
    pending.current = true
    setInvalidField('')
    setStatus('submitting')
    setError('')

    try {
      const signedInUser = await signInWithGoogle()
      if (signedInUser) {
        setStatus('idle')
      } else {
        const next = getPostAuthNavigation(null, returnPath)
        navigate(next.to, { replace: true, state: next.state })
      }
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    } finally {
      pending.current = false
    }
  }

  return {
    email,
    backPath,
    error,
    invalidField,
    handleEmailSignIn,
    handleGoogleSignIn,
    isSubmitting: isLoading || status === 'submitting',
    password,
    resetStatus,
    returnPath,
    setEmail,
    setPassword,
    setShowPassword,
    showPassword,
  }
}
