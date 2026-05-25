import {
  AuthHeader,
  AuthPanel,
} from '../../../features/auth/AuthLayoutParts.jsx'
import { AuthShell } from '../../../features/auth/AuthShell.jsx'
import { SignInForm } from '../../auth/SignInForm.jsx'
import { useAdminSignInForm } from './useAdminSignInForm.js'

function AdminSignInPage() {
  const signInForm = useAdminSignInForm()

  return (
    <AuthShell backLabel="Back" backTo="/" variant="sign-in auth-page--wide">
      <AuthPanel>
        <AuthHeader
          title="Admin sign in"
          subtitle="Use an authorized Pickup Lane admin account."
        />

        <SignInForm
          email={signInForm.email}
          error={signInForm.error}
          isSubmitting={signInForm.isSubmitting}
          onSubmit={signInForm.handleEmailSignIn}
          password={signInForm.password}
          resetStatus=""
          setEmail={signInForm.setEmail}
          setPassword={signInForm.setPassword}
          setShowPassword={signInForm.setShowPassword}
          showPassword={signInForm.showPassword}
        />
      </AuthPanel>
    </AuthShell>
  )
}

export default AdminSignInPage
