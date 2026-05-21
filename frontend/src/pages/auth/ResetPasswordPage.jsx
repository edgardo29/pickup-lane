import { Navigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import EmailVerificationAction from './EmailVerificationAction.jsx'
import PasswordResetPanel from './PasswordResetPanel.jsx'
import { usePasswordResetForm } from './usePasswordResetForm.js'
import '../../styles/auth/ResetPasswordPage.css'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const { confirmPasswordReset, refreshCurrentUserVerification, verifyPasswordReset } = useAuth()
  const mode = searchParams.get('mode') || 'resetPassword'
  const code = searchParams.get('oobCode') || ''
  const passwordReset = usePasswordResetForm({
    code,
    confirmPasswordReset,
    mode,
    verifyPasswordReset,
  })

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

  return (
    <PasswordResetPanel
      email={passwordReset.email}
      error={passwordReset.error}
      onResetPassword={passwordReset.handleResetPassword}
      password={passwordReset.password}
      setPassword={passwordReset.setPassword}
      setShowPassword={passwordReset.setShowPassword}
      showPassword={passwordReset.showPassword}
      status={passwordReset.status}
    />
  )
}
