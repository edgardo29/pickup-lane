import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LockIcon,
  MailIcon,
  SendIcon,
  ShieldCheckIcon,
} from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import {
  AuthField,
  AuthHalo,
  AuthHeader,
  AuthPanel,
  SecurityCallout,
} from '../../features/auth/AuthFormParts.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { isValidEmail } from '../../features/auth/authHelpers.js'
import '../../styles/auth/ForgotPasswordPage.css'

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
    <AuthShell backLabel="Back to sign in" backTo="/sign-in" variant="forgot-password">
      <AuthPanel>
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
