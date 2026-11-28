import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { checkEmailAvailability } from '../../lib/authApi.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import { auth } from '../../lib/firebase.js'
import { useCleanupUnfinishedSignupOnEntry, useGoogleRedirectCompletion } from '../../features/auth/authHooks.js'
import {
  getPostAuthNavigation,
  getSafeAuthBackPath,
  isValidEmail,
  isValidPassword,
} from '../../features/auth/authHelpers.js'

export function useCreateAccountForm() {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    appUser, beginEmailSignup, cleanupUnfinishedSignup, currentUser, isLoading,
    pendingGoogleSignup, pendingSignup, settleGoogleSignupRedirect, signInWithGoogle,
  } = useAuth()
  const [email, setEmail] = useState(pendingSignup?.email ?? '')
  const [password, setPassword] = useState(pendingSignup?.password ?? '')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [invalidField, setInvalidField] = useState('')
  const operation = useRef(null)
  const mounted = useRef(false)
  const returnPath = typeof location.state?.from === 'string' ? location.state.from : ''
  const backPath = typeof location.state?.backTo === 'string'
    ? location.state.backTo : getSafeAuthBackPath(returnPath)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; operation.current = null }
  }, [])

  useEffect(() => {
    const request = operation.current
    if (request?.kind === 'email' && request.uid !== currentUser?.uid) {
      operation.current = null
      setStatus('idle')
      setError('')
      setInvalidField('')
    }
  }, [currentUser?.uid])

  const { cleanupFailed, isCleaning, retryCleanup } = useCleanupUnfinishedSignupOnEntry({
    appUser, cleanupUnfinishedSignup, currentUser, isLoading, pendingGoogleSignup,
    pendingSignup, setError, disabled: status === 'submitting' || Boolean(error),
  })

  useGoogleRedirectCompletion({
    appUser, currentUser, isLoading: isLoading || status === 'submitting',
    navigate, pendingGoogleSignup, settleGoogleSignupRedirect, returnPath,
  })

  async function handleCreateAccount(event) {
    event.preventDefault()
    if (operation.current || isLoading || isCleaning || cleanupFailed) return
    setInvalidField('')
    setError('')
    const trimmedEmail = email.trim()
    if (!isValidEmail(trimmedEmail)) {
      setInvalidField('email'); setError('Enter a valid email.'); return
    }
    if (!password) {
      setInvalidField('password'); setError('Create a password.'); return
    }
    if (!isValidPassword(password)) {
      setInvalidField('password')
      setError('Password must be at least 8 characters and include a number or symbol.')
      return
    }

    const request = { kind: 'email', uid: auth.currentUser?.uid }
    operation.current = request
    setStatus('submitting')
    const isCurrent = () => mounted.current && operation.current === request
      && auth.currentUser?.uid === request.uid
    try {
      const availability = await checkEmailAvailability(trimmedEmail)
      if (!isCurrent()) return
      if (!availability.available) {
        setError('An account already exists with this email.')
        setStatus('idle'); return
      }
      beginEmailSignup({ email: trimmedEmail.toLowerCase(), password })
      navigate('/finish-profile', { state: { from: returnPath } })
    } catch {
      if (isCurrent()) { setError('Could not check this email. Please try again.'); setStatus('idle') }
    } finally {
      if (operation.current === request) operation.current = null
    }
  }

  async function handleGoogleSignIn() {
    if (operation.current || isLoading || isCleaning || cleanupFailed) return
    const request = {}
    operation.current = request
    setStatus('submitting'); setError(''); setInvalidField('')
    try {
      const signedInUser = await signInWithGoogle()
      if (!mounted.current || operation.current !== request) return
      // The signed-in route guard owns navigation once an app account is loaded.
      if (signedInUser) setStatus('idle')
      else {
        const next = getPostAuthNavigation(null, returnPath)
        navigate(next.to, { replace: true, state: next.state })
      }
    } catch (requestError) {
      if (mounted.current && operation.current === request) {
        setError(getAuthErrorMessage(requestError)); setStatus('idle')
      }
    } finally {
      if (operation.current === request) operation.current = null
    }
  }

  return {
    email, backPath, error, invalidField, cleanupFailed, retryCleanup,
    handleCreateAccount, handleGoogleSignIn,
    isSubmitting: isLoading || isCleaning || cleanupFailed || status === 'submitting',
    password, returnPath, setEmail, setPassword, setShowPassword, showPassword,
  }
}
