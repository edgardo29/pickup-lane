import { useEffect, useRef, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { applyActionCode } from 'firebase/auth'
import { ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import {
  AuthHalo,
  AuthHeader,
  AuthPanel,
} from '../../features/auth/AuthLayoutParts.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import { auth } from '../../lib/firebase.js'

function EmailVerificationAction({ code, refreshCurrentUserVerification }) {
  const [status, setStatus] = useState(code ? 'checking' : 'invalid')
  const [error, setError] = useState(code ? '' : 'This verification link is missing or invalid.')
  const actionCodeRef = useRef({ code: '', promise: null })

  useEffect(() => {
    let ignore = false

    async function verifyEmailCode() {
      if (!code) {
        return
      }

      setStatus('checking')
      setError('')

      if (actionCodeRef.current.code !== code) {
        actionCodeRef.current = { code, promise: null }
      }

      if (!actionCodeRef.current.promise) {
        actionCodeRef.current.promise = applyActionCode(auth, code)
          .then(() => ({ applied: true, error: null }))
          .catch((requestError) => ({ applied: false, error: requestError }))
      }

      const applyResult = await actionCodeRef.current.promise
      const refreshedUser = await waitForEmailVerification(
        refreshCurrentUserVerification,
        () => ignore,
      )

      if (!ignore) {
        if (refreshedUser?.email_verified_at) {
          setStatus('success')
          return
        }

        if (!applyResult.applied) {
          setError('This verification link is expired or already used.')
          setStatus('invalid')
          return
        }

        setError('')
        setStatus('unavailable')
      }
    }

    verifyEmailCode()

    return () => {
      ignore = true
    }
  }, [code, refreshCurrentUserVerification])

  return (
    <AuthShell showBack={false} variant="reset-password">
      <AuthPanel>
        <div className="auth-action-result">
          <AuthHalo icon={<ShieldCheckIcon />} />

          {status === 'checking' && (
            <AuthHeader
              title="Verifying email"
              subtitle="One moment while we verify your email."
            />
          )}

          {status === 'invalid' && (
            <>
              <AuthHeader
                title="Verification link unavailable"
                subtitle="Send a new verification email from Create Game."
              />
              <FormErrorMessage>{error}</FormErrorMessage>
              <Link className="auth-primary-button" to="/create-game">
                <ArrowRight aria-hidden="true" />
                Back to Create Game
              </Link>
            </>
          )}

          {status === 'unavailable' && (
            <>
              <AuthHeader
                title="Verification not confirmed"
                subtitle="Return to Create Game. If hosting is still locked, request a fresh verification email."
              />
              <Link className="auth-primary-button" to="/create-game">
                <ArrowRight aria-hidden="true" />
                Back to Create Game
              </Link>
            </>
          )}

          {status === 'success' && (
            <>
              <AuthHeader
                title="Email verified"
                subtitle="You can now publish a community game."
              />
              <Link className="auth-primary-button" to="/create-game">
                <ArrowRight aria-hidden="true" />
                Continue
              </Link>
            </>
          )}
        </div>
      </AuthPanel>
    </AuthShell>
  )
}

async function waitForEmailVerification(refreshCurrentUserVerification, shouldStop) {
  const maxAttempts = 3

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (shouldStop()) {
      return null
    }

    const refreshedUser = await refreshCurrentUserVerification().catch(() => null)

    if (refreshedUser?.email_verified_at) {
      return refreshedUser
    }

    if (attempt < maxAttempts - 1) {
      await wait(700)
    }
  }

  return null
}

function wait(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds)
  })
}

export default EmailVerificationAction
