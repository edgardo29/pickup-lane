import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { InfoIcon, UserIcon } from '../../components/AuthIcons.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest } from '../../lib/apiClient.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import {
  AuthField,
  AuthHeader,
  AuthPanel,
  BirthdayField,
  SecurityNote,
} from '../../features/auth/AuthFormParts.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import {
  getBirthdayValidation,
  hasCompleteProfile,
  splitDisplayName,
  splitIsoDate,
} from '../../features/auth/authHelpers.js'
import '../../styles/auth/FinishProfilePage.css'

export function FinishProfilePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    appUser,
    cleanupUnfinishedSignup,
    currentUser,
    isLoading,
    pendingSignup,
    syncCurrentFirebaseUser,
    settleGoogleSignupRedirect,
    signUpWithEmail,
    updateAppUser,
  } = useAuth()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [birthMonth, setBirthMonth] = useState('')
  const [birthDay, setBirthDay] = useState('')
  const [birthYear, setBirthYear] = useState('')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const returnPath = typeof location.state?.from === 'string' ? location.state.from : ''

  useEffect(() => {
    const displayNameParts = splitDisplayName(currentUser?.displayName)

    // Existing profile form state mirrors whichever auth source is available.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFirstName(appUser?.first_name ?? displayNameParts.firstName)
    setLastName(appUser?.last_name ?? displayNameParts.lastName)
    const birthdayParts = splitIsoDate(appUser?.date_of_birth)
    setBirthMonth(birthdayParts.month)
    setBirthDay(birthdayParts.day)
    setBirthYear(birthdayParts.year)
  }, [
    appUser?.id,
    appUser?.first_name,
    appUser?.last_name,
    appUser?.date_of_birth,
    currentUser?.displayName,
  ])

  useEffect(() => {
    if (!isLoading && !appUser?.id && !pendingSignup && !currentUser) {
      navigate('/create-account', { replace: true, state: { from: returnPath } })
    }
  }, [appUser?.id, currentUser, isLoading, navigate, pendingSignup, returnPath])

  useEffect(() => {
    if (currentUser && !pendingSignup) {
      settleGoogleSignupRedirect()
    }
  }, [currentUser, pendingSignup, settleGoogleSignupRedirect])

  async function handleBackFromProfile() {
    setError('')

    if (currentUser && !hasCompleteProfile(appUser)) {
      setStatus('submitting')

      try {
        await cleanupUnfinishedSignup()
      } catch {
        setError('Could not cancel sign-up. Please try again.')
        setStatus('idle')
        return
      }
    }

    navigate('/create-account', { state: { from: returnPath } })
  }

  async function handleFinishProfile(event) {
    event.preventDefault()
    setError('')

    const trimmedFirstName = firstName.trim()
    const trimmedLastName = lastName.trim()
    const birthdayValidation = getBirthdayValidation(birthMonth, birthDay, birthYear)

    if (!trimmedFirstName) {
      setError('Enter your first name.')
      return
    }

    if (!trimmedLastName) {
      setError('Enter your last name.')
      return
    }

    if (!birthdayValidation.isValid) {
      setError(birthdayValidation.message)
      return
    }

    setStatus('submitting')

    try {
      let userToUpdate = appUser

      if (!userToUpdate?.id) {
        if (pendingSignup) {
          userToUpdate = await signUpWithEmail(pendingSignup.email, pendingSignup.password)
        } else if (currentUser) {
          userToUpdate = await syncCurrentFirebaseUser()
        } else {
          navigate('/create-account', { replace: true, state: { from: returnPath } })
          return
        }
      }

      if (!userToUpdate?.id) {
        throw new Error('Profile sync did not finish.')
      }

      const updatedUser = await apiRequest(`/users/${userToUpdate.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date_of_birth: birthdayValidation.value,
          first_name: trimmedFirstName,
          last_name: trimmedLastName,
        }),
      })

      updateAppUser(updatedUser)
      navigate(returnPath || '/games')
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  return (
    <AuthShell
      backDisabled={status === 'submitting'}
      backLabel="Back to create account"
      onBack={handleBackFromProfile}
      variant="finish-profile auth-page--profile"
    >
      <AuthPanel>
        <AuthHeader
          title="Finish Profile"
          subtitle="Just a few details to finish setting up your account."
        />

        <form autoComplete="off" className="auth-form" onSubmit={handleFinishProfile}>
          <div className="auth-two-column">
            <AuthField
              autoComplete="off"
              disabled={isLoading || status === 'submitting'}
              icon={<UserIcon />}
              label="First Name"
              onChange={(event) => setFirstName(event.target.value)}
              placeholder="First name"
              required
              value={firstName}
            />
            <AuthField
              autoComplete="off"
              disabled={isLoading || status === 'submitting'}
              icon={<UserIcon />}
              label="Last Name"
              onChange={(event) => setLastName(event.target.value)}
              placeholder="Last name"
              required
              value={lastName}
            />
          </div>

          <BirthdayField
            day={birthDay}
            disabled={isLoading || status === 'submitting'}
            month={birthMonth}
            onDayChange={setBirthDay}
            onMonthChange={setBirthMonth}
            onYearChange={setBirthYear}
            year={birthYear}
          />

          <p className="auth-inline-note">
            <InfoIcon />
            You must be at least 13 years old to use Pickup Lane.
          </p>

          {error && <p className="auth-error">{error}</p>}

          <button
            className="auth-primary-button"
            disabled={isLoading || status === 'submitting'}
            type="submit"
          >
            {status === 'submitting' ? 'Saving...' : 'Continue'}
          </button>
        </form>

        <SecurityNote />
      </AuthPanel>
    </AuthShell>
  )
}
