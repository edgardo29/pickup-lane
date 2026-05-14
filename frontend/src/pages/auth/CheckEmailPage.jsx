import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { CheckEmailIcon, MailIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import {
  AuthHalo,
  AuthHeader,
  AuthPanel,
  AuthStep,
} from '../../features/auth/AuthFormParts.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import '../../styles/auth/CheckEmailPage.css'

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
    <AuthShell backLabel="Back to sign in" backTo="/sign-in" variant="check-email">
      <AuthPanel>
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
