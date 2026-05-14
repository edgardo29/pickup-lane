import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { LockIcon, MailIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { checkEmailAvailability } from '../../lib/authApi.js'
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
import { getPostAuthPath, isValidEmail, isValidPassword } from '../../features/auth/authHelpers.js'
import '../../styles/auth/CreateAccountPage.css'

export function CreateAccountPage() {
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

  return (
    <AuthShell backLabel="Back" backTo={returnPath || '/'} variant="create-account auth-page--wide">
      <AuthPanel>
        <AuthHeader title="Create Account" subtitle="Create your Pickup Lane account to get started." />

        <ProviderButtons disabled={status === 'submitting'} onGoogle={handleGoogleSignIn} />

        <Divider label="or create with email" />

        <form className="auth-form" noValidate onSubmit={handleCreateAccount}>
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
            autoComplete="new-password"
            hint="At least 8 characters with a number or symbol"
            icon={<LockIcon />}
            label="Password"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Create a password"
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

          <button className="auth-primary-button" disabled={status === 'submitting'} type="submit">
            {status === 'submitting' ? 'Checking...' : 'Create Account'}
          </button>
        </form>

        <AuthSwitch
          text="Already have an account?"
          to="/sign-in"
          label="Sign In"
          state={{ from: returnPath }}
        />

        <p className="auth-terms">
          By creating an account, you agree to our{' '}
          <Link state={{ from: '/create-account', fromLabel: 'Back to Create Account' }} to="/terms">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link state={{ from: '/create-account', fromLabel: 'Back to Create Account' }} to="/privacy">
            Privacy Policy
          </Link>.
        </p>
      </AuthPanel>
    </AuthShell>
  )
}
