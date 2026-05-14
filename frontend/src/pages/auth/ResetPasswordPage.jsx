import { Link, useSearchParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { LockIcon, ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
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
