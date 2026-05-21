import {
  AuthHeader,
  AuthPanel,
  AuthSwitch,
  Divider,
} from '../../features/auth/AuthLayoutParts.jsx'
import { ProviderButtons } from '../../features/auth/AuthProviderButtons.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { SignInForm } from './SignInForm.jsx'
import { useSignInForm } from './useSignInForm.js'
import '../../styles/auth/SignInPage.css'

export function SignInPage() {
  const signInForm = useSignInForm()

  return (
    <AuthShell backLabel="Back" backTo={signInForm.returnPath || '/'} variant="sign-in auth-page--wide">
      <AuthPanel>
        <AuthHeader title="Welcome back" subtitle="Sign in to your Pickup Lane account." />

        <ProviderButtons disabled={signInForm.isSubmitting} onGoogle={signInForm.handleGoogleSignIn} />

        <Divider label="or sign in with email" />

        <SignInForm
          email={signInForm.email}
          error={signInForm.error}
          isSubmitting={signInForm.isSubmitting}
          onSubmit={signInForm.handleEmailSignIn}
          password={signInForm.password}
          resetStatus={signInForm.resetStatus}
          setEmail={signInForm.setEmail}
          setPassword={signInForm.setPassword}
          setShowPassword={signInForm.setShowPassword}
          showPassword={signInForm.showPassword}
        />

        <AuthSwitch
          text="Don’t have an account?"
          to="/create-account"
          label="Create Account"
          state={{ from: signInForm.returnPath }}
        />
      </AuthPanel>
    </AuthShell>
  )
}
