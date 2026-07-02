import { useState } from 'react'
import {
  AuthHeader,
  AuthPanel,
  AuthSwitch,
  Divider,
} from '../../features/auth/AuthLayoutParts.jsx'
import { ProviderButtons } from '../../features/auth/AuthProviderButtons.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { LegalPolicyModal } from '../../features/legal/LegalPolicyModal.jsx'
import { LEGAL_POLICY_IDS } from '../../features/legal/legalPolicies.js'
import { CreateAccountForm } from './CreateAccountForm.jsx'
import { useCreateAccountForm } from './useCreateAccountForm.js'
import '../../styles/auth/CreateAccountPage.css'

export function CreateAccountPage() {
  const accountForm = useCreateAccountForm()
  const [activeLegalPolicyId, setActiveLegalPolicyId] = useState('')

  return (
    <AuthShell backLabel="Back" backTo={accountForm.backPath || '/'} variant="create-account auth-page--wide">
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
          state={{ backTo: accountForm.backPath, from: accountForm.returnPath }}
        />

        <p className="auth-terms">
          By creating an account, you agree to our{' '}
          <button
            className="auth-terms__button"
            type="button"
            onClick={() => setActiveLegalPolicyId(LEGAL_POLICY_IDS.terms)}
          >
            Terms of Service
          </button>{' '}
          and{' '}
          <button
            className="auth-terms__button"
            type="button"
            onClick={() => setActiveLegalPolicyId(LEGAL_POLICY_IDS.privacy)}
          >
            Privacy Policy
          </button>.
        </p>
      </AuthPanel>

      {activeLegalPolicyId && (
        <LegalPolicyModal
          policyId={activeLegalPolicyId}
          onClose={() => setActiveLegalPolicyId('')}
        />
      )}
    </AuthShell>
  )
}
