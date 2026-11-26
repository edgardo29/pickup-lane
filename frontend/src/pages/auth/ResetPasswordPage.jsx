import { Navigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import EmailVerificationAction from './EmailVerificationAction.jsx'
import PasswordResetPanel from './PasswordResetPanel.jsx'
import { usePasswordResetForm } from './usePasswordResetForm.js'
import '../../styles/auth/ResetPasswordPage.css'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const { confirmPasswordReset, currentUser, isLoading, refreshCurrentUserVerification, verifyPasswordReset } = useAuth()
  const mode = searchParams.get('mode') || 'resetPassword'
  const code = searchParams.get('oobCode') || ''
  if (mode === 'verifyEmail') {
    return (
      <EmailVerificationAction
        key={`${currentUser?.uid || 'signed-out'}:${code}`}
        code={code}
        isAuthLoading={isLoading}
        continueUrl={searchParams.get('continueUrl')}
        refreshCurrentUserVerification={refreshCurrentUserVerification}
      />
    )
  }

  if (mode !== 'resetPassword') {
    return <Navigate replace to="/sign-in" />
  }

  return (
    <PasswordResetContent
      key={code}
      code={code}
      confirmPasswordReset={confirmPasswordReset}
      verifyPasswordReset={verifyPasswordReset}
    />
  )
}

// A new link owns a fresh form; pending work from the previous form is discarded.
function PasswordResetContent({ code, confirmPasswordReset, verifyPasswordReset }) {
  const passwordReset = usePasswordResetForm({
    code,
    confirmPasswordReset,
    mode: 'resetPassword',
    verifyPasswordReset,
  })
  return (
    <PasswordResetPanel
      email={passwordReset.email}
      error={passwordReset.error}
      onResetPassword={passwordReset.handleResetPassword}
      password={passwordReset.password}
      passwordInvalid={passwordReset.passwordInvalid}
      setPassword={passwordReset.setPassword}
      setShowPassword={passwordReset.setShowPassword}
      showPassword={passwordReset.showPassword}
      status={passwordReset.status}
    />
  )
}
