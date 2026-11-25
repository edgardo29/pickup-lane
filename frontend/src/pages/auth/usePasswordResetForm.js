import { useEffect, useEffectEvent, useRef, useState } from 'react'
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
  const isMounted = useRef(false)
  const [passwordInvalid, setPasswordInvalid] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [status, setStatus] = useState(code && mode === 'resetPassword' ? 'checking' : 'invalid')
  const [error, setError] = useState(code ? '' : 'This reset link is missing or invalid.')

  // Authentication callbacks can change without changing the reset link.
  const checkResetCode = useEffectEvent((resetCode) => verifyPasswordReset(resetCode))

  useEffect(() => {
    let ignore = false
    isMounted.current = true

    async function verifyResetCode() {
      if (!code || mode !== 'resetPassword') {
        return
      }

      setStatus('checking')
      setError('')

      try {
        const resetEmail = await checkResetCode(code)

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
      isMounted.current = false
    }
  }, [code, mode])

  async function handleResetPassword(event) {
    event.preventDefault()
    if (status !== 'ready') return
    setError('')
    setPasswordInvalid(false)

    if (!isValidPassword(password)) {
      setPasswordInvalid(true)
      setError('Password must be at least 8 characters and include a number or symbol.')
      return
    }

    setStatus('submitting')

    try {
      await confirmPasswordReset(code, password)
      if (!isMounted.current) return
      setPassword('')
      setStatus('success')
    } catch (requestError) {
      if (!isMounted.current) return
      setError(getPasswordResetLinkError(requestError))
      if (['auth/expired-action-code', 'auth/invalid-action-code'].includes(requestError?.code)) {
        setPassword('')
        setShowPassword(false)
        setStatus('invalid')
      } else {
        setPasswordInvalid(requestError?.code === 'auth/weak-password')
        setStatus('ready')
      }
    }
  }

  return {
    email,
    error,
    handleResetPassword,
    password,
    passwordInvalid,
    setPassword,
    setShowPassword,
    showPassword,
    status,
  }
}
