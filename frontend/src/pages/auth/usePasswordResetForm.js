import { useEffect, useState } from 'react'
import {
  getPasswordResetLinkError,
  isValidPassword,
} from '../../features/auth/authHelpers.js'

export function usePasswordResetForm({
  code,
  confirmPasswordReset,
  mode,
  verifyPasswordReset,
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState(code && mode === 'resetPassword' ? 'checking' : 'invalid')
  const [error, setError] = useState(code ? '' : 'This reset link is missing or invalid.')

  useEffect(() => {
    let ignore = false

    async function verifyResetCode() {
      if (!code || mode !== 'resetPassword') {
        return
      }

      setStatus('checking')
      setError('')

      try {
        const resetEmail = await verifyPasswordReset(code)

        if (!ignore) {
          setEmail(resetEmail)
          setStatus('ready')
        }
      } catch (requestError) {
        if (!ignore) {
          setError(getPasswordResetLinkError(requestError))
          setStatus('invalid')
        }
      }
    }

    verifyResetCode()

    return () => {
      ignore = true
    }
  }, [code, mode, verifyPasswordReset])

  async function handleResetPassword(event) {
    event.preventDefault()
    setError('')

    if (!isValidPassword(password)) {
      setError('Password must be at least 8 characters and include a number or symbol.')
      return
    }

    setStatus('submitting')

    try {
      await confirmPasswordReset(code, password)
      setPassword('')
      setStatus('success')
    } catch (requestError) {
      setError(getPasswordResetLinkError(requestError))
      setStatus('ready')
    }
  }

  return {
    email,
    error,
    handleResetPassword,
    password,
    setPassword,
    setShowPassword,
    showPassword,
    status,
  }
}
