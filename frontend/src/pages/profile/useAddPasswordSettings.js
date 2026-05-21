import { useState } from 'react'
import { getAuthErrorMessage } from '../../lib/authErrors.js'
import { isValidPassword } from './profileValidation.js'

export function useAddPasswordSettings({ addPasswordToCurrentAccount }) {
  const [isPasswordOpen, setIsPasswordOpen] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [passwordStatus, setPasswordStatus] = useState('idle')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')

  function openPasswordModal() {
    setNewPassword('')
    setConfirmPassword('')
    setShowNewPassword(false)
    setPasswordError('')
    setPasswordSuccess('')
    setPasswordStatus('idle')
    setIsPasswordOpen(true)
  }

  const handleAddPassword = async (event) => {
    event.preventDefault()
    setPasswordStatus('saving')
    setPasswordError('')
    setPasswordSuccess('')

    if (!isValidPassword(newPassword)) {
      setPasswordError('Password must be at least 8 characters and include a number or symbol.')
      setPasswordStatus('idle')
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match.')
      setPasswordStatus('idle')
      return
    }

    try {
      await addPasswordToCurrentAccount(newPassword)
      setNewPassword('')
      setConfirmPassword('')
      setPasswordSuccess('Password added.')
      setPasswordStatus('idle')
    } catch (requestError) {
      setPasswordError(getAuthErrorMessage(requestError))
      setPasswordStatus('idle')
    }
  }

  return {
    confirmPassword,
    handleAddPassword,
    isPasswordOpen,
    newPassword,
    openPasswordModal,
    passwordError,
    passwordStatus,
    passwordSuccess,
    setConfirmPassword,
    setIsPasswordOpen,
    setNewPassword,
    setShowNewPassword,
    showNewPassword,
  }
}
