import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useState } from 'react'
import { LockIcon, MailIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import {
  AuthField,
  AuthHeader,
  AuthPanel,
  AuthSwitch,
  Divider,
  PasswordVisibilityButton,
  ProviderButtons,
} from '../../features/auth/AuthFormParts.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { useCleanupUnfinishedSignupOnEntry, useGoogleRedirectCompletion } from '../../features/auth/authHooks.js'
import { getPostAuthPath, isValidEmail } from '../../features/auth/authHelpers.js'
import '../../styles/auth/SignInPage.css'

export function SignInPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const {
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
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
      navigate(returnPath || getPostAuthPath(signedInUser))
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
        navigate(returnPath || getPostAuthPath(signedInUser))
      } else {
        navigate('/finish-profile', { state: { from: returnPath } })
      }
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell backLabel="Back" backTo={returnPath || '/'} variant="sign-in auth-page--wide">
      <AuthPanel>
        <AuthHeader title="Welcome back" subtitle="Sign in to your Pickup Lane account." />

        <ProviderButtons disabled={status === 'submitting'} onGoogle={handleGoogleSignIn} />

        <Divider label="or sign in with email" />

        <form className="auth-form" noValidate onSubmit={handleEmailSignIn}>
          <AuthField
            autoComplete="email"
            icon={<MailIcon />}
            inputMode="email"
            label="Email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Enter your email"
            required
            value={email}
          />

          <AuthField
            action={<Link to="/forgot-password">Forgot?</Link>}
            autoComplete="current-password"
            icon={<LockIcon />}
            label="Password"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            required
            trailingAction={
              <PasswordVisibilityButton
                isVisible={showPassword}
                onClick={() => setShowPassword((current) => !current)}
              />
            }
            type={showPassword ? 'text' : 'password'}
            value={password}
          />

          {error && <p className="auth-error">{error}</p>}
          {resetStatus === 'success' && !error && (
            <p className="auth-success">Password changed.</p>
          )}

          <button
            className="auth-primary-button auth-primary-button--muted"
            disabled={status === 'submitting'}
            type="submit"
          >
            {status === 'submitting' ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <AuthSwitch
          text="Don’t have an account?"
          to="/create-account"
          label="Create Account"
          state={{ from: returnPath }}
        />
      </AuthPanel>
    </AuthShell>
  )
}
