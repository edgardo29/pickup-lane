import { UserPlus } from 'lucide-react'
import { LockIcon, MailIcon } from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  AuthField,
  PasswordVisibilityButton,
} from '../../features/auth/AuthFields.jsx'

export function CreateAccountForm({
  email,
  error,
  isSubmitting,
  invalidField,
  onSubmit,
  password,
  setEmail,
  setPassword,
  setShowPassword,
  showPassword,
}) {
  return (
    <form className="auth-form" noValidate onSubmit={onSubmit}>
      <AuthField
        aria-describedby={invalidField === 'email' ? 'create-account-error' : undefined}
        aria-invalid={invalidField === 'email'}
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
        aria-describedby={invalidField === 'password' ? 'create-account-error' : undefined}
        aria-invalid={invalidField === 'password'}
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

      <FormErrorMessage id="create-account-error">{error}</FormErrorMessage>

      <button className="auth-primary-button" disabled={isSubmitting} type="submit">
        <UserPlus aria-hidden="true" />
        {isSubmitting ? 'Checking...' : 'Create Account'}
      </button>
    </form>
  )
}
