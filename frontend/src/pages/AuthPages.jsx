import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import BrandMark from '../components/BrandMark.jsx'
import {
  ArrowLeftIcon,
  AppleIcon,
  CheckEmailIcon,
  GoogleIcon,
  InfoIcon,
  LockIcon,
  MailIcon,
  SendIcon,
  ShieldCheckIcon,
  UserIcon,
} from '../components/AuthIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { apiRequest } from '../lib/apiClient.js'
import { getAuthErrorMessage } from '../lib/authErrors.js'
import { checkEmailAvailability } from '../lib/authApi.js'
import '../styles/auth.css'

const securityText = 'Your information is secure and will never be shared.'
const monthOptions = [
  ['01', 'January'],
  ['02', 'February'],
  ['03', 'March'],
  ['04', 'April'],
  ['05', 'May'],
  ['06', 'June'],
  ['07', 'July'],
  ['08', 'August'],
  ['09', 'September'],
  ['10', 'October'],
  ['11', 'November'],
  ['12', 'December'],
]

export function SignInPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const {
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    signInWithEmail,
    signInWithGoogle,
  } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const resetStatus = searchParams.get('reset')

  useCleanupUnfinishedSignupOnEntry({
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    setError,
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
      navigate(getPostAuthPath(signedInUser))
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
      navigate(getPostAuthPath(signedInUser))
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Sign in to Pickup Lane"
      subtitle="Jump back into your games, messages, and saved spots."
      variant="wide"
    >
      <AuthPanel>
        <AuthHeader title="Welcome back" subtitle="Sign in to your Pickup Lane account." />

        <ProviderButtons
          disabled={status === 'submitting'}
          onGoogle={handleGoogleSignIn}
        />

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

        <AuthSwitch text="Don’t have an account?" to="/create-account" label="Create Account" />
      </AuthPanel>
    </AuthShell>
  )
}

export function CreateAccountPage() {
  const navigate = useNavigate()
  const {
    appUser,
    beginEmailSignup,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    signInWithGoogle,
  } = useAuth()
  const [email, setEmail] = useState(pendingSignup?.email ?? '')
  const [password, setPassword] = useState(pendingSignup?.password ?? '')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  useCleanupUnfinishedSignupOnEntry({
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    setError,
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
      navigate('/finish-profile')
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
      navigate(getPostAuthPath(signedInUser))
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell
      eyebrow="Create account"
      title="Start playing faster"
      subtitle="Use social sign-in or create a Pickup Lane account with email."
      variant="wide"
    >
      <AuthPanel>
        <AuthHeader title="Create Account" subtitle="Create your Pickup Lane account to get started." />

        <ProviderButtons
          disabled={status === 'submitting'}
          onGoogle={handleGoogleSignIn}
        />

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

        <AuthSwitch text="Already have an account?" to="/sign-in" label="Sign In" />

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

export function FinishProfilePage() {
  const navigate = useNavigate()
  const {
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingSignup,
    syncCurrentFirebaseUser,
    settleGoogleSignupRedirect,
    signUpWithEmail,
    updateAppUser,
  } = useAuth()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [birthMonth, setBirthMonth] = useState('')
  const [birthDay, setBirthDay] = useState('')
  const [birthYear, setBirthYear] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  useEffect(() => {
    const displayNameParts = splitDisplayName(currentUser?.displayName)

    setFirstName(appUser?.first_name ?? displayNameParts.firstName)
    setLastName(appUser?.last_name ?? displayNameParts.lastName)
    const birthdayParts = splitIsoDate(appUser?.date_of_birth)
    setBirthMonth(birthdayParts.month)
    setBirthDay(birthdayParts.day)
    setBirthYear(birthdayParts.year)
  }, [
    appUser?.id,
    appUser?.first_name,
    appUser?.last_name,
    appUser?.date_of_birth,
    currentUser?.displayName,
  ])

  useEffect(() => {
    if (!isLoading && !appUser?.id && !pendingSignup && !currentUser) {
      navigate('/create-account', { replace: true })
    }
  }, [appUser?.id, currentUser, isLoading, navigate, pendingSignup])

  useEffect(() => {
    if (currentUser && !pendingSignup) {
      settleGoogleSignupRedirect()
    }
  }, [currentUser, pendingSignup, settleGoogleSignupRedirect])

  async function handleBackFromProfile() {
    setError('')

    if (currentUser && !hasCompleteProfile(appUser)) {
      setStatus('submitting')

      try {
        await cleanupUnfinishedSignup()
      } catch {
        setError('Could not cancel sign-up. Please try again.')
        setStatus('idle')
        return
      }
    }

    navigate('/create-account')
  }

  async function handleFinishProfile(event) {
    event.preventDefault()
    setError('')

    const trimmedFirstName = firstName.trim()
    const trimmedLastName = lastName.trim()
    const birthdayValidation = getBirthdayValidation(birthMonth, birthDay, birthYear)

    if (!trimmedFirstName) {
      setError('Enter your first name.')
      return
    }

    if (!trimmedLastName) {
      setError('Enter your last name.')
      return
    }

    if (!birthdayValidation.isValid) {
      setError(birthdayValidation.message)
      return
    }

    setStatus('submitting')

    try {
      let userToUpdate = appUser

      if (!userToUpdate?.id) {
        if (pendingSignup) {
          userToUpdate = await signUpWithEmail(pendingSignup.email, pendingSignup.password)
        } else if (currentUser) {
          userToUpdate = await syncCurrentFirebaseUser()
        } else {
          navigate('/create-account', { replace: true })
          return
        }
      }

      if (!userToUpdate?.id) {
        throw new Error('Profile sync did not finish.')
      }

      const updatedUser = await apiRequest(`/users/${userToUpdate.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date_of_birth: birthdayValidation.value,
          first_name: trimmedFirstName,
          last_name: trimmedLastName,
        }),
      })

      updateAppUser(updatedUser)
      navigate('/games')
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell
      eyebrow="Profile setup"
      title="Finish your player profile"
      subtitle="A few details help us keep games organized and age appropriate."
    >
      <AuthPanel>
        <BackButton
          disabled={status === 'submitting'}
          label="Back to create account"
          onClick={handleBackFromProfile}
        />
        <AuthHeader
          title="Finish Profile"
          subtitle="Just a few details to finish setting up your account."
        />

        <form autoComplete="off" className="auth-form" onSubmit={handleFinishProfile}>
          <div className="auth-two-column">
            <AuthField
              autoComplete="off"
              disabled={isLoading || status === 'submitting'}
              icon={<UserIcon />}
              label="First Name"
              onChange={(event) => setFirstName(event.target.value)}
              placeholder="First name"
              required
              value={firstName}
            />
            <AuthField
              autoComplete="off"
              disabled={isLoading || status === 'submitting'}
              icon={<UserIcon />}
              label="Last Name"
              onChange={(event) => setLastName(event.target.value)}
              placeholder="Last name"
              required
              value={lastName}
            />
          </div>

          <BirthdayField
            day={birthDay}
            disabled={isLoading || status === 'submitting'}
            month={birthMonth}
            onDayChange={setBirthDay}
            onMonthChange={setBirthMonth}
            onYearChange={setBirthYear}
            year={birthYear}
          />

          <p className="auth-inline-note">
            <InfoIcon />
            You must be at least 13 years old to use Pickup Lane.
          </p>

          {error && <p className="auth-error">{error}</p>}

          <button
            className="auth-primary-button"
            disabled={isLoading || status === 'submitting'}
            type="submit"
          >
            {status === 'submitting' ? 'Saving...' : 'Continue'}
          </button>
        </form>

        <SecurityNote />
      </AuthPanel>
    </AuthShell>
  )
}

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const { sendPasswordReset } = useAuth()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  async function handleResetPassword(event) {
    event.preventDefault()
    setStatus('submitting')
    setError('')

    const trimmedEmail = email.trim()

    if (!isValidEmail(trimmedEmail)) {
      setError('Enter a valid email.')
      setStatus('idle')
      return
    }

    try {
      await sendPasswordReset(trimmedEmail)
      navigate('/check-email', { state: { email: trimmedEmail.toLowerCase() } })
    } catch (requestError) {
      if (requestError?.code?.includes('auth/user-not-found')) {
        navigate('/check-email', { state: { email: trimmedEmail.toLowerCase() } })
        return
      }

      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell
      eyebrow="Password help"
      title="Reset access securely"
      subtitle="Send a password reset link and get back to your games."
    >
      <AuthPanel>
        <BackLink />
        <AuthHalo icon={<LockIcon />} />
        <AuthHeader
          title="Forgot Password?"
          subtitle="No worries. Enter your email and we’ll send you a link to reset your password."
        />

        <form className="auth-form" noValidate onSubmit={handleResetPassword}>
          <AuthField
            autoComplete="email"
            icon={<MailIcon />}
            inputMode="email"
            label="Email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Enter your email"
            required
            type="email"
            value={email}
          />

          {error && <p className="auth-error">{error}</p>}

          <button className="auth-primary-button" disabled={status === 'submitting'} type="submit">
            <SendIcon />
            {status === 'submitting' ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        <SecurityCallout
          icon={<ShieldCheckIcon />}
          title="Secure reset"
          text="For your security, we’ll send a private reset link that expires automatically."
        />
      </AuthPanel>
    </AuthShell>
  )
}

export function CheckEmailPage() {
  const location = useLocation()
  const { sendPasswordReset } = useAuth()
  const email = location.state?.email || ''
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleResend() {
    if (!email) {
      return
    }

    setStatus('submitting')
    setMessage('')
    setError('')

    try {
      await sendPasswordReset(email)
      setMessage('Reset email sent again.')
      setStatus('idle')
    } catch (requestError) {
      if (requestError?.code?.includes('auth/user-not-found')) {
        setMessage('Reset email sent again.')
        setStatus('idle')
        return
      }

      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell
      eyebrow="Reset sent"
      title="Check your email"
      subtitle="Your reset link is on the way. Keep this page handy in case you need another one."
    >
      <AuthPanel>
        <BackLink />
        <AuthHalo icon={<CheckEmailIcon />} />
        <AuthHeader
          title="Check your email"
          subtitle={
            email ? (
              <>
                If an account exists, we sent a password reset link to <strong>{email}</strong>.
              </>
            ) : (
              'If the email matches an account, a reset link is on the way.'
            )
          }
        />

        <div className="auth-steps">
          <AuthStep
            title="It may take a few minutes to arrive."
            text="Check your inbox and spam folder."
          />
          <AuthStep title="Click the link in the email" text="to reset your password." />
          <AuthStep title="The link will expire in 60 minutes" text="for your security." />
        </div>

        <button
          className="auth-resend-card"
          disabled={!email || status === 'submitting'}
          onClick={handleResend}
          type="button"
        >
          <MailIcon />
          <span>{status === 'submitting' ? 'Sending...' : 'Resend email'}</span>
          <strong>{email ? 'Ready' : 'Go back'}</strong>
        </button>

        {message && <p className="auth-success">{message}</p>}
        {error && <p className="auth-error">{error}</p>}

        <Link className="auth-text-link" to="/forgot-password">
          Didn’t receive the email?
        </Link>

        <Link className="auth-primary-button" to="/sign-in">
          Back to Sign In
        </Link>
      </AuthPanel>
    </AuthShell>
  )
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const { confirmPasswordReset, verifyPasswordReset } = useAuth()
  const code = searchParams.get('oobCode') || ''
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState(code ? 'checking' : 'invalid')
  const [error, setError] = useState(code ? '' : 'This reset link is missing or invalid.')

  useEffect(() => {
    let ignore = false

    async function verifyResetCode() {
      if (!code) {
        return
      }

      setStatus('checking')
      setError('')

      try {
        const resetEmail = await verifyPasswordReset(code)

        if (!ignore) {
          setEmail(resetEmail)
          setStatus('ready')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(getPasswordResetLinkError(requestError))
          setStatus('invalid')
        }
      }
    }

    verifyResetCode()

    return () => {
      ignore = true
    }
  }, [code, verifyPasswordReset])

  async function handleResetPassword(event) {
    event.preventDefault()
    setError('')

    if (!isValidPassword(password)) {
      setError('Password must be at least 8 characters and include a number or symbol.')
      return
    }

    setStatus('submitting')

    try {
      await confirmPasswordReset(code, password)
      setPassword('')
      setStatus('success')
    } catch (requestError) {
      setError(getPasswordResetLinkError(requestError))
      setStatus('ready')
    }
  }

  return (
    <AuthShell
      eyebrow="Password reset"
      title="Create a new password"
      subtitle="Reset your password securely and get back into Pickup Lane."
    >
      <AuthPanel>
        <BackLink />
        <AuthHalo icon={status === 'success' ? <ShieldCheckIcon /> : <LockIcon />} />

        {status === 'checking' && (
          <AuthHeader
            title="Checking reset link"
            subtitle="One moment while we verify your password reset link."
          />
        )}

        {status === 'invalid' && (
          <>
            <AuthHeader
              title="Reset link expired"
              subtitle="This password reset link is invalid or has already been used."
            />
            {error && <p className="auth-error">{error}</p>}
            <Link className="auth-primary-button" to="/forgot-password">
              Send New Link
            </Link>
          </>
        )}

        {status === 'success' && (
          <>
            <AuthHeader
              title="Password changed"
              subtitle="You can now sign in with your new password."
            />
            <Link className="auth-primary-button" to="/sign-in">
              Back to Sign In
            </Link>
          </>
        )}

        {(status === 'ready' || status === 'submitting') && (
          <>
            <AuthHeader
              title="Reset your password"
              subtitle={
                email ? (
                  <>
                    Create a new password for <strong>{email}</strong>.
                  </>
                ) : (
                  'Create a new password for your account.'
                )
              }
            />

            <form className="auth-form" noValidate onSubmit={handleResetPassword}>
              <AuthField
                autoComplete="new-password"
                hint="At least 8 characters with a number or symbol"
                icon={<LockIcon />}
                label="New password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter new password"
                required
                trailingAction={
                  <PasswordVisibilityButton
                    isVisible={showPassword}
                    onClick={() => setShowPassword((isVisible) => !isVisible)}
                  />
                }
                type={showPassword ? 'text' : 'password'}
                value={password}
              />

              {error && <p className="auth-error">{error}</p>}

              <button
                className="auth-primary-button"
                disabled={status === 'submitting'}
                type="submit"
              >
                {status === 'submitting' ? 'Saving...' : 'Save Password'}
              </button>
            </form>
          </>
        )}
      </AuthPanel>
    </AuthShell>
  )
}

function AuthShell({ children, variant = 'default' }) {
  return (
    <main className={`auth-page auth-page--${variant}`}>
      <Link className="auth-home-link" to="/">
        <ArrowLeftIcon />
        Home
      </Link>

      <div className="auth-frame">
        <Link className="auth-frame__brand" to="/" aria-label="Pickup Lane home">
          <BrandMark compact />
        </Link>

        {children}
      </div>
    </main>
  )
}

function AuthPanel({ children }) {
  return <section className="auth-panel">{children}</section>
}

function AuthHeader({ title, subtitle }) {
  return (
    <header className="auth-header">
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </header>
  )
}

function ProviderButtons({ disabled = false, onGoogle }) {
  return (
    <div className="auth-provider-grid">
      <button disabled={disabled} type="button" onClick={onGoogle}>
        <GoogleIcon />
        Continue with Google
      </button>
      <button disabled type="button" title="Apple sign-in will be added later.">
        <AppleIcon />
        Continue with Apple
      </button>
    </div>
  )
}

function useCleanupUnfinishedSignupOnEntry({
  appUser,
  cleanupUnfinishedSignup,
  currentUser,
  isLoading,
  pendingGoogleSignup,
  pendingSignup,
  setError,
}) {
  useEffect(() => {
    let ignore = false

    async function cleanup() {
      if (
        isLoading ||
        !currentUser ||
        appUser?.id ||
        pendingGoogleSignup ||
        pendingSignup
      ) {
        return
      }

      try {
        await cleanupUnfinishedSignup()
      } catch {
        if (!ignore) {
          setError('Could not reset the previous sign-up. Please try again.')
        }
      }
    }

    cleanup()

    return () => {
      ignore = true
    }
  }, [
    appUser?.id,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingGoogleSignup,
    pendingSignup,
    setError,
  ])
}

function AuthField({
  action,
  hint,
  icon,
  label,
  placeholder,
  trailingAction,
  type = 'text',
  ...inputProps
}) {
  return (
    <label className="auth-field">
      <span className="auth-field__label">
        {label}
        {action}
      </span>
      <span className={`auth-field__input ${trailingAction ? 'auth-field__input--with-action' : ''}`}>
        {icon}
        <input {...inputProps} placeholder={placeholder} type={type} />
        {trailingAction}
      </span>
      {hint && <small>{hint}</small>}
    </label>
  )
}

function BirthdayField({
  day,
  disabled,
  month,
  onDayChange,
  onMonthChange,
  onYearChange,
  year,
}) {
  const maxDay = getDaysInMonth(month, year)
  const dayOptions = Array.from({ length: maxDay }, (_, index) => pad2(index + 1))
  const yearOptions = getBirthYearOptions()

  function updateMonth(nextMonth) {
    onMonthChange(nextMonth)

    if (day && Number(day) > getDaysInMonth(nextMonth, year)) {
      onDayChange('')
    }
  }

  function updateYear(nextYear) {
    onYearChange(nextYear)

    if (day && Number(day) > getDaysInMonth(month, nextYear)) {
      onDayChange('')
    }
  }

  return (
    <fieldset className="auth-field auth-birthday-field" disabled={disabled}>
      <legend className="auth-field__label">Date of Birth</legend>
      <div className="auth-birthday-grid">
        <label className="auth-select-field">
          <span>Month</span>
          <select
            aria-label="Birth month"
            onChange={(event) => updateMonth(event.target.value)}
            value={month}
          >
            <option value="">Month</option>
            {monthOptions.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-select-field">
          <span>Day</span>
          <select
            aria-label="Birth day"
            onChange={(event) => onDayChange(event.target.value)}
            value={day}
          >
            <option value="">Day</option>
            {dayOptions.map((value) => (
              <option key={value} value={value}>
                {Number(value)}
              </option>
            ))}
          </select>
        </label>
        <label className="auth-select-field">
          <span>Year</span>
          <select
            aria-label="Birth year"
            onChange={(event) => updateYear(event.target.value)}
            value={year}
          >
            <option value="">Year</option>
            {yearOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>
    </fieldset>
  )
}

function PasswordVisibilityButton({ isVisible, onClick }) {
  return (
    <button
      aria-label={isVisible ? 'Hide password' : 'Show password'}
      className="auth-password-toggle"
      onClick={onClick}
      type="button"
    >
      {isVisible ? <EyeOffIcon /> : <EyeIcon />}
    </button>
  )
}

function getPostAuthPath(user) {
  return hasCompleteProfile(user) ? '/games' : '/finish-profile'
}

function hasCompleteProfile(user) {
  return Boolean(
    user?.first_name?.trim?.() &&
      user?.last_name?.trim?.() &&
      user?.date_of_birth,
  )
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

function isValidPassword(value) {
  return value.length >= 8 && /[\d\W_]/.test(value)
}

function getPasswordResetLinkError(error) {
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

function splitIsoDate(dateString) {
  if (!dateString || !/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
    return { day: '', month: '', year: '' }
  }

  const [year, month, day] = dateString.split('-')
  return { day, month, year }
}

function splitDisplayName(displayName) {
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

function getBirthdayValidation(month, day, year) {
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

function getBirthYearOptions() {
  const currentYear = new Date().getFullYear()

  return Array.from({ length: 101 }, (_, index) => String(currentYear - index))
}

function getDaysInMonth(month, year) {
  const monthNumber = Number(month)

  if (!monthNumber) {
    return 31
  }

  const yearNumber = Number(year) || 2000
  return new Date(yearNumber, monthNumber, 0).getDate()
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m3 3 18 18" />
      <path d="M10.6 10.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-1.2" />
      <path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6 0 9.5 7 9.5 7a14.2 14.2 0 0 1-2.7 3.4" />
      <path d="M6.6 6.6C3.9 8.2 2.5 12 2.5 12s3.5 7 9.5 7c1.6 0 3-.4 4.2-1" />
    </svg>
  )
}

function AuthHalo({ icon }) {
  return <div className="auth-halo">{icon}</div>
}

function BackLink({ label = 'Back to sign in', to = '/sign-in' }) {
  return (
    <Link className="auth-back-link" to={to} aria-label={label}>
      <ArrowLeftIcon />
    </Link>
  )
}

function BackButton({ disabled = false, label, onClick }) {
  return (
    <button
      aria-label={label}
      className="auth-back-link"
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      <ArrowLeftIcon />
    </button>
  )
}

function Divider({ label }) {
  return (
    <div className="auth-divider">
      <span />
      {label}
      <span />
    </div>
  )
}

function AuthSwitch({ label, text, to }) {
  return (
    <p className="auth-switch">
      {text} <Link to={to}>{label}</Link>
    </p>
  )
}

function SecurityNote() {
  return (
    <p className="auth-secure-note">
      <LockIcon />
      {securityText}
    </p>
  )
}

function SecurityCallout({ icon, text, title }) {
  return (
    <div className="auth-security-callout">
      {icon}
      <p>
        <strong>{title}</strong>
        {text}
      </p>
    </div>
  )
}

function AuthStep({ title, text }) {
  return (
    <div className="auth-step">
      <span />
      <p>
        <strong>{title}</strong>
        {text}
      </p>
    </div>
  )
}
