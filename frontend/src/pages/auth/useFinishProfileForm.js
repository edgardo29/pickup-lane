import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth.js'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import {
  getBirthdayValidation,
  hasCompleteProfile,
  splitDisplayName,
  splitIsoDate,
} from '../../features/auth/authHelpers.js'
import { updateSignupProfile } from './finishProfileApi.js'

export function useFinishProfileForm() {
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

      const updatedUser = await updateSignupProfile(userToUpdate.id, {
        dateOfBirth: birthdayValidation.value,
        firstName: trimmedFirstName,
        lastName: trimmedLastName,
      })

      updateAppUser(updatedUser)
      navigate(returnPath || '/games')
    } catch (requestError) {
      setError(getAuthErrorMessage(requestError))
      setStatus('idle')
    }
  }

  const isSubmitting = status === 'submitting'
  const isDisabled = isLoading || isSubmitting

  return {
    birthDay,
    birthMonth,
    birthYear,
    error,
    firstName,
    handleBackFromProfile,
    handleFinishProfile,
    isDisabled,
    isSubmitting,
    lastName,
    setBirthDay,
    setBirthMonth,
    setBirthYear,
    setFirstName,
    setLastName,
  }
}
