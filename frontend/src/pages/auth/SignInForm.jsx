import { LogIn } from 'lucide-react'
import { Link } from 'react-router-dom'
import { LockIcon, MailIcon } from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  AuthField,
  PasswordVisibilityButton,
} from '../../features/auth/AuthFields.jsx'

export function SignInForm({
  email,
  error,
  invalidField,
  isSubmitting,
  onSubmit,
  password,
  resetStatus,
  setEmail,
  setPassword,
  setShowPassword,
  showPassword,
}) {
  return (
    <form className="auth-form" noValidate onSubmit={onSubmit}>
      <AuthField
        aria-invalid={invalidField === 'email' || undefined}
        aria-describedby={invalidField === 'email' ? 'sign-in-error' : undefined}
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
        aria-invalid={invalidField === 'password' || undefined}
        aria-describedby={invalidField === 'password' ? 'sign-in-error' : undefined}
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

      <FormErrorMessage id="sign-in-error">{error}</FormErrorMessage>
      {resetStatus === 'success' && !error && (
        <p className="auth-success" role="status">Password changed.</p>
      )}

      <button
        className="auth-primary-button"
        disabled={isSubmitting}
        type="submit"
      >
        <LogIn aria-hidden="true" />
        {isSubmitting ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  )
}
