import { useCallback, useMemo, useRef, useState } from 'react'
import { getAuthErrorMessage } from '../lib/authErrors.js'
import {
  EMAIL_PASSWORD_PROVIDER_ID,
  GOOGLE_PROVIDER_ID,
} from '../lib/reauthentication.js'
import {
  StepUpCancelledError,
  runStepUpProtectedAction,
} from '../lib/stepUpAction.js'
import { useAuth } from '../hooks/useAuth.js'
import { StepUpContext } from './stepUpContext.js'
import '../styles/auth/StepUp.css'

export function StepUpProvider({ children }) {
  const {
    getReauthenticationProviderId,
    reauthenticateWithGoogle,
    reauthenticateWithPassword,
  } = useAuth()
  const pendingRequestRef = useRef(null)
  const [requestState, setRequestState] = useState(null)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const closeRequest = useCallback((outcome) => {
    const pendingRequest = pendingRequestRef.current
    pendingRequestRef.current = null
    setRequestState(null)
    setPassword('')
    setError('')
    setIsSubmitting(false)

    if (!pendingRequest) {
      return
    }

    if (outcome === 'success') {
      pendingRequest.resolve()
      return
    }

    pendingRequest.reject(new StepUpCancelledError())
  }, [])

  const requestStepUp = useCallback(({ actionLabel = '' } = {}) => (
    new Promise((resolve, reject) => {
      const providerId = getReauthenticationProviderId?.() || ''
      if (!providerId) {
        reject(new Error('Identity confirmation is not available for this sign-in method.'))
        return
      }

      if (pendingRequestRef.current) {
        reject(new Error('Identity confirmation is already in progress.'))
        return
      }

      pendingRequestRef.current = { resolve, reject }
      setRequestState({ actionLabel, providerId })
      setPassword('')
      setError('')
      setIsSubmitting(false)
    })
  ), [getReauthenticationProviderId])

  const runWithStepUp = useCallback((action, options = {}) => (
    runStepUpProtectedAction({
      action,
      requestStepUp: () => requestStepUp(options),
    })
  ), [requestStepUp])

  const confirmStepUp = useCallback((options = {}) => requestStepUp(options), [
    requestStepUp,
  ])

  async function submitStepUp(event) {
    event.preventDefault()
    if (!requestState || isSubmitting) {
      return
    }

    if (requestState.providerId === EMAIL_PASSWORD_PROVIDER_ID && !password) {
      setError('Password is required.')
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      if (requestState.providerId === GOOGLE_PROVIDER_ID) {
        await reauthenticateWithGoogle()
      } else {
        await reauthenticateWithPassword(password)
      }
      closeRequest('success')
    } catch (reauthError) {
      setError(getAuthErrorMessage(reauthError))
      setIsSubmitting(false)
    }
  }

  function cancelStepUp() {
    if (!isSubmitting) {
      closeRequest('cancel')
    }
  }

  const contextValue = useMemo(
    () => ({
      confirmStepUp,
      runWithStepUp,
    }),
    [confirmStepUp, runWithStepUp],
  )

  return (
    <StepUpContext.Provider value={contextValue}>
      {children}
      {requestState && (
        <div className="step-up-backdrop" role="presentation" onClick={cancelStepUp}>
          <section
            aria-labelledby="step-up-title"
            aria-modal="true"
            className="step-up-modal"
            role="dialog"
            onClick={(event) => event.stopPropagation()}
          >
            <header className="step-up-modal__header">
              <h2 id="step-up-title">Confirm identity</h2>
              <p>
                {requestState.actionLabel
                  ? `Confirm identity to ${requestState.actionLabel}.`
                  : 'Confirm identity to continue.'}
              </p>
            </header>

            <form className="step-up-modal__form" onSubmit={submitStepUp}>
              {requestState.providerId === EMAIL_PASSWORD_PROVIDER_ID && (
                <label className="step-up-modal__field">
                  <span>Password</span>
                  <input
                    autoComplete="current-password"
                    autoFocus
                    disabled={isSubmitting}
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>
              )}

              {error && <p className="step-up-modal__error">{error}</p>}

              <div className="step-up-modal__actions">
                <button disabled={isSubmitting} type="button" onClick={cancelStepUp}>
                  Cancel
                </button>
                <button
                  className="step-up-modal__primary"
                  disabled={isSubmitting}
                  type="submit"
                >
                  {isSubmitting
                    ? 'Confirming'
                    : requestState.providerId === GOOGLE_PROVIDER_ID
                      ? 'Continue with Google'
                      : 'Confirm'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </StepUpContext.Provider>
  )
}
