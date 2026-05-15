import { Link, Navigate, useSearchParams } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { applyActionCode } from 'firebase/auth'
import { LockIcon, ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { auth } from '../../lib/firebase.js'
import {
  AuthField,
  AuthHalo,
  AuthHeader,
  AuthPanel,
  PasswordVisibilityButton,
} from '../../features/auth/AuthFormParts.jsx'
import {
  getPasswordResetLinkError,
  isValidPassword,
} from '../../features/auth/authHelpers.js'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import '../../styles/auth/ResetPasswordPage.css'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const { confirmPasswordReset, refreshCurrentUserVerification, verifyPasswordReset } = useAuth()
  const mode = searchParams.get('mode') || 'resetPassword'
  const code = searchParams.get('oobCode') || ''
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState(code && mode === 'resetPassword' ? 'checking' : 'invalid')
  const [error, setError] = useState(code ? '' : 'This reset link is missing or invalid.')

  useEffect(() => {
    let ignore = false

    async function verifyResetCode() {
      if (!code || mode !== 'resetPassword') {
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
  }, [code, mode, verifyPasswordReset])

  if (mode === 'verifyEmail') {
    return (
      <EmailVerificationAction
        code={code}
        refreshCurrentUserVerification={refreshCurrentUserVerification}
      />
    )
  }

  if (mode !== 'resetPassword') {
    return <Navigate replace to="/sign-in" />
  }

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
    <AuthShell backLabel="Back to sign in" backTo="/sign-in" variant="reset-password">
      <AuthPanel>
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

function EmailVerificationAction({ code, refreshCurrentUserVerification }) {
  const [status, setStatus] = useState(code ? 'checking' : 'invalid')
  const [error, setError] = useState(code ? '' : 'This verification link is missing or invalid.')
  const processedCodeRef = useRef('')

  useEffect(() => {
    let ignore = false

    async function verifyEmailCode() {
      if (!code || processedCodeRef.current === code) {
        return
      }

      processedCodeRef.current = code
      setStatus('checking')
      setError('')

      let appliedCode = false

      try {
        await applyActionCode(auth, code)
        appliedCode = true
      } catch {
        // Firebase may report a reused code after the email has already been
        // verified. We still give the signed-in user a chance to refresh below.
      }

      if (appliedCode) {
        refreshCurrentUserVerification().catch(() => {})

        if (!ignore) {
          setStatus('success')
        }

        return
      }

      const refreshedUser = await waitForEmailVerification(
        refreshCurrentUserVerification,
        () => ignore,
      )

      if (!ignore) {
        if (refreshedUser?.email_verified_at) {
          setStatus('success')
          return
        }

        setError('')
        setStatus('unavailable')
      }
    }

    verifyEmailCode()

    return () => {
      ignore = true
    }
  }, [code, refreshCurrentUserVerification])

  return (
    <AuthShell backLabel="Back to create game" backTo="/create-game" variant="reset-password">
      <AuthPanel>
        <div className="auth-action-result">
          <AuthHalo icon={<ShieldCheckIcon />} />

          {status === 'checking' && (
            <AuthHeader
              title="Verifying email"
              subtitle="One moment while we verify your email."
            />
          )}

          {status === 'invalid' && (
            <>
              <AuthHeader
                title="Verification link unavailable"
                subtitle="Send a new verification email from Create Game."
              />
              {error && <p className="auth-error">{error}</p>}
              <Link className="auth-primary-button" to="/create-game">
                Back to Create Game
              </Link>
            </>
          )}

          {status === 'unavailable' && (
            <>
              <AuthHeader
                title="Verification not confirmed"
                subtitle="Return to Create Game. If hosting is still locked, request a fresh verification email."
              />
              <Link className="auth-primary-button" to="/create-game">
                Back to Create Game
              </Link>
            </>
          )}

          {status === 'success' && (
            <>
              <AuthHeader
                title="Email verified"
                subtitle="You can now publish a community game."
              />
              <Link className="auth-primary-button" to="/create-game">
                Continue
              </Link>
            </>
          )}
        </div>
      </AuthPanel>
    </AuthShell>
  )
}

async function waitForEmailVerification(refreshCurrentUserVerification, shouldStop) {
  const maxAttempts = 3

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (shouldStop()) {
      return null
    }

    const refreshedUser = await refreshCurrentUserVerification().catch(() => null)

    if (refreshedUser?.email_verified_at) {
      return refreshedUser
    }

    if (attempt < maxAttempts - 1) {
      await wait(700)
    }
  }

  return null
}

function wait(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds)
  })
}
