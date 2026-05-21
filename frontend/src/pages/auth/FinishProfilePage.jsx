import {
  AuthHeader,
  AuthPanel,
} from '../../features/auth/AuthLayoutParts.jsx'
import { SecurityNote } from '../../features/auth/AuthSecurity.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { FinishProfileForm } from './FinishProfileForm.jsx'
import { useFinishProfileForm } from './useFinishProfileForm.js'
import '../../styles/auth/FinishProfilePage.css'

export function FinishProfilePage() {
  const profileForm = useFinishProfileForm()

  return (
    <AuthShell
      backDisabled={profileForm.isSubmitting}
      backLabel="Back to create account"
      onBack={profileForm.handleBackFromProfile}
      variant="finish-profile auth-page--profile"
    >
      <AuthPanel>
        <AuthHeader
          title="Finish Profile"
          subtitle="Just a few details to finish setting up your account."
        />

        <FinishProfileForm
          birthDay={profileForm.birthDay}
          birthMonth={profileForm.birthMonth}
          birthYear={profileForm.birthYear}
          error={profileForm.error}
          firstName={profileForm.firstName}
          isDisabled={profileForm.isDisabled}
          isSubmitting={profileForm.isSubmitting}
          lastName={profileForm.lastName}
          onSubmit={profileForm.handleFinishProfile}
          setBirthDay={profileForm.setBirthDay}
          setBirthMonth={profileForm.setBirthMonth}
          setBirthYear={profileForm.setBirthYear}
          setFirstName={profileForm.setFirstName}
          setLastName={profileForm.setLastName}
        />

        <SecurityNote />
      </AuthPanel>
    </AuthShell>
  )
}
