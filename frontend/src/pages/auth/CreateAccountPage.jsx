import { Link } from 'react-router-dom'
import {
  AuthHeader,
  AuthPanel,
  AuthSwitch,
  Divider,
} from '../../features/auth/AuthLayoutParts.jsx'
import { ProviderButtons } from '../../features/auth/AuthProviderButtons.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { CreateAccountForm } from './CreateAccountForm.jsx'
import { useCreateAccountForm } from './useCreateAccountForm.js'
import '../../styles/auth/CreateAccountPage.css'

export function CreateAccountPage() {
  const accountForm = useCreateAccountForm()

  return (
    <AuthShell backLabel="Back" backTo={accountForm.returnPath || '/'} variant="create-account auth-page--wide">
      <AuthPanel>
        <AuthHeader title="Create Account" subtitle="Create your Pickup Lane account to get started." />

        <ProviderButtons disabled={accountForm.isSubmitting} onGoogle={accountForm.handleGoogleSignIn} />

        <Divider label="or create with email" />

        <CreateAccountForm
          email={accountForm.email}
          error={accountForm.error}
          isSubmitting={accountForm.isSubmitting}
          onSubmit={accountForm.handleCreateAccount}
          password={accountForm.password}
          setEmail={accountForm.setEmail}
          setPassword={accountForm.setPassword}
          setShowPassword={accountForm.setShowPassword}
          showPassword={accountForm.showPassword}
        />

        <AuthSwitch
          text="Already have an account?"
          to="/sign-in"
          label="Sign In"
          state={{ from: accountForm.returnPath }}
        />

        <p className="auth-terms">
          By creating an account, you agree to our{' '}
          <Link state={{ from: '/create-account', fromLabel: 'Back to Create Account' }} to="/terms">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link state={{ from: '/create-account', fromLabel: 'Back to Create Account' }} to="/privacy">
            Privacy Policy
          </Link>.
        </p>
      </AuthPanel>
    </AuthShell>
  )
}
