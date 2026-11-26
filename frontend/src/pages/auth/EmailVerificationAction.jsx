import { useEffect, useEffectEvent, useRef, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { applyActionCode } from 'firebase/auth'
import { ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import { FormErrorMessage } from '../../components/FormErrorMessage.jsx'
import { AuthHalo, AuthHeader, AuthPanel } from '../../features/auth/AuthLayoutParts.jsx'
import { AuthShell } from '../../features/auth/AuthShell.jsx'
import {
  CREATE_SUB_RETURN, getVerificationReturnPath, verificationReturnLink,
} from '../../features/email-verification/emailVerificationReturn.js'
import { auth } from '../../lib/firebase.js'

function EmailVerificationAction({ code, continueUrl, isAuthLoading, refreshCurrentUserVerification }) {
  const [result, setResult] = useState({ status: code ? 'checking' : 'invalid', error: code ? '' : 'This verification link is missing or invalid.' })
  const applicationRef = useRef(null)
  const refreshVerification = useEffectEvent(() => refreshCurrentUserVerification())
  const destination = getVerificationReturnPath(continueUrl)
  const returnLabel = destination === CREATE_SUB_RETURN ? 'Create Sub Post' : 'Create Game'

  useEffect(() => {
    if (!code || isAuthLoading) return undefined
    const controller = new AbortController()
    if (!applicationRef.current) {
      applicationRef.current = applyActionCode(auth, code)
        .then(() => ({ applied: true }))
        .catch((error) => ({ applied: false, error }))
    }
    async function verify() {
      const applied = await applicationRef.current
      for (let attempt = 0; attempt < 3 && !controller.signal.aborted; attempt += 1) {
        const account = await refreshVerification().catch(() => null)
        if (controller.signal.aborted) return
        if (account?.email_verified_at) {
          setResult({ status: 'success', error: '' })
          return
        }
        if (attempt < 2) await waitForRefresh(controller.signal)
      }
      if (controller.signal.aborted) return
      const invalidCode = ['auth/expired-action-code', 'auth/invalid-action-code'].includes(applied.error?.code)
      setResult(!applied.applied && invalidCode
        ? { status: 'invalid', error: 'This verification link is expired or already used.' }
        : { status: 'unavailable', error: '' })
    }
    verify()
    return () => controller.abort()
  }, [code, isAuthLoading])

  const titles = { checking: 'Verifying email', success: 'Email verified', invalid: 'Verification link unavailable', unavailable: 'Verification not confirmed' }
  const subtitles = {
    checking: 'One moment while we verify your email.',
    success: 'Your account email is verified. Continue to your form to finish publishing.',
    invalid: `Request a fresh verification email from ${returnLabel}.`,
    unavailable: `We could not confirm your account verification. Return to ${returnLabel} to check again or request a fresh email.`,
  }
  return (
    <AuthShell showBack={false} variant="reset-password">
      <AuthPanel>
        <div className="auth-action-result">
          <AuthHalo icon={<ShieldCheckIcon />} />
          <div role="status" aria-live="polite" aria-atomic="true">
            <AuthHeader title={titles[result.status]} subtitle={subtitles[result.status]} />
          </div>
          <FormErrorMessage>{result.error}</FormErrorMessage>
          {result.status !== 'checking' && (
            <Link className="auth-primary-button" to={verificationReturnLink(destination)}>
              <ArrowRight aria-hidden="true" />
              {result.status === 'success' ? 'Continue' : `Back to ${returnLabel}`}
            </Link>
          )}
        </div>
      </AuthPanel>
    </AuthShell>
  )
}

function waitForRefresh(signal) {
  return new Promise((resolve) => {
    function finish() {
      window.clearTimeout(timeout)
      signal.removeEventListener('abort', finish)
      resolve()
    }
    const timeout = window.setTimeout(finish, 700)
    signal.addEventListener('abort', finish, { once: true })
  })
}

export default EmailVerificationAction
