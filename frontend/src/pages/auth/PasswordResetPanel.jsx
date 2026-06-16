import { Check, LogIn } from 'lucide-react'
import { Link } from 'react-router-dom'
import { LockIcon, SendIcon, ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  AuthHalo,
  AuthHeader,
  AuthPanel,
} from '../../features/auth/AuthLayoutParts.jsx'
import {
  AuthField,
  PasswordVisibilityButton,
} from '../../features/auth/AuthFields.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'

function PasswordResetPanel({
  email,
  error,
  onResetPassword,
  password,
  setPassword,
  setShowPassword,
  showPassword,
  status,
}) {
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
            <FormErrorMessage>{error}</FormErrorMessage>
            <Link className="auth-primary-button" to="/forgot-password">
              <SendIcon />
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
              <LogIn aria-hidden="true" />
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

            <form className="auth-form" noValidate onSubmit={onResetPassword}>
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

              <FormErrorMessage>{error}</FormErrorMessage>

              <button
                className="auth-primary-button"
                disabled={status === 'submitting'}
                type="submit"
              >
                <Check aria-hidden="true" />
                {status === 'submitting' ? 'Saving...' : 'Save Password'}
              </button>
            </form>
          </>
        )}
      </AuthPanel>
    </AuthShell>
  )
}

export default PasswordResetPanel
