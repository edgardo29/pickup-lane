import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LockIcon,
  MailIcon,
  SendIcon,
  ShieldCheckIcon,
} from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import {
  AuthHalo,
  AuthHeader,
  AuthPanel,
} from '../../features/auth/AuthLayoutParts.jsx'
import { AuthField } from '../../features/auth/AuthFields.jsx'
import { SecurityCallout } from '../../features/auth/AuthSecurity.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { isValidEmail } from '../../features/auth/authHelpers.js'
import '../../styles/auth/ForgotPasswordPage.css'

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const { sendPasswordReset } = useAuth()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [emailError, setEmailError] = useState('')
  const isMounted = useRef(false)

  useEffect(() => {
    isMounted.current = true
    return () => {
      isMounted.current = false
    }
  }, [])

  async function handleResetPassword(event) {
    event.preventDefault()
    setStatus('submitting')
    setError('')
    setEmailError('')

    const trimmedEmail = email.trim()

    if (!isValidEmail(trimmedEmail)) {
      setEmailError('Enter a valid email.')
      setStatus('idle')
      return
    }

    try {
      await sendPasswordReset(trimmedEmail)
      if (!isMounted.current) return

      navigate('/check-email', { state: { email: trimmedEmail.toLowerCase() } })
    } catch (requestError) {
      if (!isMounted.current) return

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
            aria-describedby={emailError ? 'forgot-password-email-error' : undefined}
            aria-invalid={Boolean(emailError)}
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

          {emailError && (
            <div id="forgot-password-email-error">
              <FormErrorMessage>{emailError}</FormErrorMessage>
            </div>
          )}
          <FormErrorMessage>{error}</FormErrorMessage>

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
