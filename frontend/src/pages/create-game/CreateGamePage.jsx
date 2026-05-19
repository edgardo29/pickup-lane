import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftIcon } from '../../components/AuthIcons.jsx'
import BrowseAppNav from '../../components/BrowseAppNav.jsx'
import { useAuth } from '../../hooks/useAuth.js'
import { apiRequest } from '../../lib/apiClient.js'
import '../../styles/browse-games/BrowseGamesPage.css'
import '../../styles/create-game.css'
import { DiscardModal } from './CreateGameControls.jsx'
import { CreateGamePreview, PublishedState } from './CreateGamePreview.jsx'
import { BasicsStep, LocationStep, NotesStep, ReviewStep, StepRail } from './CreateGameSteps.jsx'
import {
  loadEditableGame,
  loadHostPublishFees,
  patchJson,
  postJson,
  publishCommunityGame,
} from './createGameApi.js'
import { buildCommunityPublishPayload, buildHostEditPayload } from './createGamePayloads.js'
import {
  buildCommunityGameDetailPayload,
  buildReview,
  getExitPath,
  initialForm,
  mapGameToForm,
  steps,
  validateCreateGame,
  validateStep,
} from './createGameUtils.js'

function CreateGamePage() {
  const navigate = useNavigate()
  const { gameId } = useParams()
  const {
    appUser,
    isLoading,
    refreshCurrentUserVerification,
    sendCurrentUserVerificationEmail,
  } = useAuth()
  const isEditMode = Boolean(gameId)
  const [activeStep, setActiveStep] = useState(1)
  const [form, setForm] = useState(initialForm)
  const [formBaseline, setFormBaseline] = useState(initialForm)
  const [currentUser, setCurrentUser] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState(null)
  const [firstPublishIsFree, setFirstPublishIsFree] = useState(true)
  const [communityGameDetailId, setCommunityGameDetailId] = useState('')
  const [createdGameId, setCreatedGameId] = useState('')
  const [status, setStatus] = useState('idle')
  const [loadError, setLoadError] = useState('')
  const [publishError, setPublishError] = useState('')
  const [stepError, setStepError] = useState('')
  const [verificationError, setVerificationError] = useState('')
  const [verificationNotice, setVerificationNotice] = useState('')
  const [verificationStatus, setVerificationStatus] = useState('idle')
  const [verificationCooldownUntil, setVerificationCooldownUntil] = useState(0)
  const [verificationCooldownSeconds, setVerificationCooldownSeconds] = useState(0)
  const [showDiscardModal, setShowDiscardModal] = useState(false)
  const blockedVerificationRefreshRef = useRef('')
  const visibleUser = currentUser || appUser
  const isWaitingForUser = isLoading && !visibleUser
  const isHostEmailVerified = Boolean(visibleUser?.email_verified_at)
  const shouldBlockForEmailVerification = visibleUser && !isEditMode && !isHostEmailVerified

  useEffect(() => {
    let ignore = false

    async function loadVerifiedContext(effectiveAppUser) {
      const [paymentMethods, gameContext, hostPublishFees] = await Promise.all([
        apiRequest(`/user-payment-methods?user_id=${effectiveAppUser.id}`),
        isEditMode ? loadEditableGame(gameId) : Promise.resolve(null),
        loadHostPublishFees(effectiveAppUser.id),
      ])

      if (ignore) {
        return
      }

      setCurrentUser(effectiveAppUser)
      setPaymentMethod(paymentMethods.find((method) => method.is_default) || paymentMethods[0] || null)
      setFirstPublishIsFree(
        !hostPublishFees.some((fee) => fee.waiver_reason === 'first_game_free'),
      )

      if (gameContext) {
        const editableForm = mapGameToForm(
          gameContext.game,
          gameContext.venue,
          gameContext.communityDetails,
        )
        setCommunityGameDetailId(gameContext.communityDetails?.id || '')
        setForm(editableForm)
        setFormBaseline(editableForm)
      } else {
        setCommunityGameDetailId('')
        setForm(initialForm)
        setFormBaseline(initialForm)
      }
    }

    async function refreshBlockedHost() {
      const refreshedAppUser = await refreshCurrentUserVerification().catch(() => null)

      if (!refreshedAppUser?.email_verified_at || ignore) {
        return
      }

      clearEmailVerificationCooldown(refreshedAppUser.id)
      setVerificationCooldownUntil(0)
      setVerificationCooldownSeconds(0)
      setVerificationError('')
      setVerificationNotice('')
      setVerificationStatus('idle')
      await loadVerifiedContext(refreshedAppUser)
    }

    async function loadCreateGameContext() {
      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to create a game.')
        }

        if (!ignore) {
          setLoadError('')
          setCurrentUser(appUser)
        }

        if (!isEditMode && !appUser.email_verified_at) {
          if (!ignore) {
            setPaymentMethod(null)
            setFirstPublishIsFree(true)
            setCommunityGameDetailId('')
            setCreatedGameId('')
            setForm(initialForm)
            setFormBaseline(initialForm)
          }

          if (blockedVerificationRefreshRef.current !== appUser.id) {
            blockedVerificationRefreshRef.current = appUser.id
            refreshBlockedHost()
          }
          return
        }

        blockedVerificationRefreshRef.current = ''
        await loadVerifiedContext(appUser)
      } catch (error) {
        if (!ignore) {
          setLoadError(error instanceof Error ? error.message : 'Unable to load create game data.')
        }
      }
    }

    loadCreateGameContext()

    return () => {
      ignore = true
    }
  }, [appUser, gameId, isEditMode, isLoading, refreshCurrentUserVerification])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (!appUser?.id || appUser.email_verified_at) {
        if (appUser?.id) {
          clearEmailVerificationCooldown(appUser.id)
        }
        setVerificationCooldownUntil(0)
        setVerificationCooldownSeconds(0)
        return
      }

      const storedCooldownUntil = getEmailVerificationCooldown(appUser.id)
      setVerificationCooldownUntil(storedCooldownUntil)
      setVerificationCooldownSeconds(getRemainingCooldownSeconds(storedCooldownUntil))
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [appUser?.email_verified_at, appUser?.id])

  useEffect(() => {
    if (!shouldBlockForEmailVerification || !visibleUser?.id) {
      return undefined
    }

    async function refreshIfVerified() {
      const refreshedAppUser = await refreshCurrentUserVerification().catch(() => null)

      if (!refreshedAppUser?.email_verified_at) {
        return
      }

      clearEmailVerificationCooldown(refreshedAppUser.id)
      setVerificationCooldownUntil(0)
      setVerificationCooldownSeconds(0)
      setVerificationError('')
      setVerificationNotice('')
      setVerificationStatus('idle')
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'visible') {
        refreshIfVerified()
      }
    }

    window.addEventListener('focus', refreshIfVerified)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('focus', refreshIfVerified)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [refreshCurrentUserVerification, shouldBlockForEmailVerification, visibleUser?.id])

  useEffect(() => {
    if (verificationCooldownUntil <= Date.now()) {
      const timeoutId = window.setTimeout(() => {
        setVerificationCooldownSeconds(0)
      }, 0)

      return () => window.clearTimeout(timeoutId)
    }

    const timeoutId = window.setTimeout(() => {
      setVerificationCooldownSeconds(getRemainingCooldownSeconds(verificationCooldownUntil))
    }, 0)

    const intervalId = window.setInterval(() => {
      const remainingSeconds = getRemainingCooldownSeconds(verificationCooldownUntil)
      setVerificationCooldownSeconds(remainingSeconds)

      if (remainingSeconds <= 0) {
        window.clearInterval(intervalId)
      }
    }, 1000)

    return () => {
      window.clearTimeout(timeoutId)
      window.clearInterval(intervalId)
    }
  }, [verificationCooldownUntil])

  const review = useMemo(() => buildReview(form), [form])
  const hasUnsavedChanges = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(formBaseline),
    [form, formBaseline],
  )
  function updateField(field, value) {
    setStepError('')
    setPublishError('')
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function goNext() {
    const error = validateStep(activeStep, form)
    if (error) {
      setStepError(error)
      return
    }

    setActiveStep((step) => Math.min(step + 1, steps.length))
  }

  function goBack() {
    if (activeStep > 1) {
      setActiveStep((step) => step - 1)
      return
    }

    requestCancel()
  }

  function requestCancel() {
    if (hasUnsavedChanges) {
      setShowDiscardModal(true)
      return
    }

    navigate(getExitPath(isEditMode, gameId))
  }

  function discardGame() {
    setShowDiscardModal(false)
    navigate(getExitPath(isEditMode, gameId))
  }

  async function submitGame() {
    if (!currentUser) {
      setPublishError('Demo user is not loaded yet.')
      return
    }

    if (!isEditMode && !isHostEmailVerified) {
      setPublishError('Verify your email before publishing.')
      return
    }

    const error = validateCreateGame(form)
    if (error) {
      setPublishError('')
      setStepError(error.message)
      setActiveStep(error.step)
      return
    }

    setStatus('publishing')
    setPublishError('')

    try {
      if (isEditMode) {
        await patchJson(`/games/${gameId}/host-edit`, buildHostEditPayload(form, currentUser))

        const communityGameDetailPayload = buildCommunityGameDetailPayload(form, gameId)
        if (communityGameDetailId) {
          await patchJson(
            `/community-game-details/${communityGameDetailId}`,
            communityGameDetailPayload,
          )
        } else {
          await postJson('/community-game-details', communityGameDetailPayload)
        }

        navigate(`/games/${gameId}`)
        return
      }

      const game = await publishCommunityGame(
        buildCommunityPublishPayload(form, currentUser, paymentMethod),
      )

      setCreatedGameId(game.id)
      setStatus('published')
    } catch (error) {
      setStatus('idle')
      setPublishError(error instanceof Error ? error.message : 'Unable to publish game.')
    }
  }

  if (status === 'published') {
    return <PublishedState gameId={createdGameId} />
  }

  return (
    <div className="create-game-page">
      <BrowseAppNav />

      <main className="create-game-shell">
        <header className="create-game-topbar">
          <button type="button" onClick={goBack} aria-label="Go back">
            <ArrowLeftIcon />
          </button>
          <div>
            <p>Host a community game</p>
            <h1>{isEditMode ? 'Edit Game' : 'Create Game'}</h1>
          </div>
          <span>Step {activeStep} of {steps.length}</span>
        </header>

        <StepRail activeStep={activeStep} />

        {loadError && <p className="create-game-error">{loadError}</p>}

        {isWaitingForUser ? (
          <section className="create-game-blocker">
            <div>
              <p>Loading</p>
              <h2>Loading Create Game</h2>
              <span>One moment while your account loads.</span>
            </div>
          </section>
        ) : shouldBlockForEmailVerification ? (
          <EmailVerificationBlocker
            cooldownSeconds={verificationCooldownSeconds}
            error={verificationError}
            notice={verificationNotice}
            status={verificationStatus}
            onSend={sendEmailVerificationLink}
          />
        ) : visibleUser ? (
          <section className="create-game-layout">
            <div className="create-game-panel">
              {activeStep === 1 && <BasicsStep form={form} updateField={updateField} />}
              {activeStep === 2 && <LocationStep form={form} updateField={updateField} />}
              {activeStep === 3 && <NotesStep form={form} updateField={updateField} />}
              {activeStep === 4 && (
                <ReviewStep
                  firstPublishIsFree={firstPublishIsFree}
                  form={form}
                  isEditMode={isEditMode}
                  publishError={publishError}
                  review={review}
                />
              )}

              {stepError && <p className="create-game-error">{stepError}</p>}

              <div className="create-game-actions">
                <button className="create-game-cancel" type="button" onClick={requestCancel}>
                  Cancel
                </button>
                <div className="create-game-actions__right">
                  {activeStep > 1 && (
                    <button className="create-game-secondary" type="button" onClick={goBack}>
                      Back
                    </button>
                  )}
                  {activeStep < steps.length ? (
                    <button className="create-game-primary" type="button" onClick={goNext}>
                      Next: {steps[activeStep].label}
                      <span aria-hidden="true">→</span>
                    </button>
                  ) : (
                    <button
                      className="create-game-primary"
                      disabled={!currentUser || status === 'publishing'}
                      type="button"
                      onClick={submitGame}
                    >
                      {status === 'publishing'
                        ? isEditMode
                          ? 'Saving...'
                          : 'Publishing...'
                        : isEditMode
                          ? 'Save Changes'
                          : 'Publish Game'}
                      <span aria-hidden="true">→</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            <CreateGamePreview
              firstPublishIsFree={firstPublishIsFree}
              form={form}
              review={review}
            />
          </section>
        ) : null}
      </main>

      {showDiscardModal && (
        <DiscardModal onClose={() => setShowDiscardModal(false)} onDiscard={discardGame} />
      )}
    </div>
  )

  async function sendEmailVerificationLink() {
    const activeUserId = appUser?.id || visibleUser?.id
    const storedCooldownUntil = getEmailVerificationCooldown(activeUserId)
    const storedCooldownSeconds = getRemainingCooldownSeconds(storedCooldownUntil)

    if (verificationCooldownSeconds > 0 || storedCooldownSeconds > 0) {
      if (storedCooldownSeconds > 0) {
        setVerificationCooldownUntil(storedCooldownUntil)
        setVerificationCooldownSeconds(storedCooldownSeconds)
      }
      return
    }

    setVerificationError('')
    setVerificationNotice('')
    setVerificationStatus('sending')

    try {
      await sendCurrentUserVerificationEmail()
      setVerificationStatus('sent')
      startEmailVerificationCooldown(activeUserId, 60)
    } catch (error) {
      const verificationMessage = getEmailVerificationErrorMessage(error)
      setVerificationError(verificationMessage.message)
      if (verificationMessage.cooldownSeconds > 0) {
        startEmailVerificationCooldown(activeUserId, verificationMessage.cooldownSeconds)
      }
      setVerificationStatus('idle')
    }
  }

  function startEmailVerificationCooldown(userId, seconds) {
    const cooldownUntil = Date.now() + seconds * 1000

    setEmailVerificationCooldown(userId, cooldownUntil)
    setVerificationCooldownUntil(cooldownUntil)
    setVerificationCooldownSeconds(seconds)
  }

}

function EmailVerificationBlocker({ cooldownSeconds, error, notice, onSend, status }) {
  const isSending = status === 'sending'
  const isCoolingDown = cooldownSeconds > 0
  const buttonLabel = isSending
    ? 'Sending...'
    : isCoolingDown
      ? `Try again in ${cooldownSeconds}s`
      : status === 'sent'
        ? 'Resend verification email'
        : 'Send verification email'

  return (
    <section className="create-game-blocker">
      <div>
        <p>{status === 'sent' ? 'Email verification sent' : 'Email verification required'}</p>
        <h2>{status === 'sent' ? 'Check your email to continue.' : 'Verify your email to become a host.'}</h2>
        <span>
          {status === 'sent'
            ? 'We sent a verification link to your email. Check your inbox or spam folder, then open the link to verify your account.'
            : 'Before you can publish a community game, we need to confirm your email address. This helps keep host accounts real and protects players from fake listings.'}
        </span>
      </div>
      <div className="create-game-blocker__actions">
        <button
          className="create-game-primary"
          disabled={isSending || isCoolingDown}
          type="button"
          onClick={onSend}
        >
          {buttonLabel}
        </button>
        {notice && <strong className="create-game-blocker__notice">{notice}</strong>}
        {error && <strong className="create-game-blocker__error">{error}</strong>}
      </div>
    </section>
  )
}

function getEmailVerificationErrorMessage(error) {
  const code = error?.code || ''
  const message = error?.message || ''
  const normalizedError = `${code} ${message}`.toLowerCase()

  if (normalizedError.includes('too-many-requests')) {
    return {
      cooldownSeconds: 300,
      message: 'Too many verification emails were sent. Try again in a few minutes.',
    }
  }

  if (normalizedError.includes('network-request-failed') || normalizedError.includes('failed to fetch')) {
    return {
      cooldownSeconds: 0,
      message: 'Network issue. Check your connection and try again.',
    }
  }

  if (normalizedError.includes('requires-recent-login')) {
    return {
      cooldownSeconds: 0,
      message: 'Sign in again, then resend the verification email.',
    }
  }

  return {
    cooldownSeconds: 0,
    message: 'Unable to send verification email right now. Please try again in a minute.',
  }
}

function getEmailVerificationCooldownKey(userId) {
  return `pickup-lane:email-verification-cooldown:${userId}`
}

function getEmailVerificationCooldown(userId) {
  if (!userId) {
    return 0
  }

  try {
    const storedValue = window.localStorage.getItem(getEmailVerificationCooldownKey(userId))
    const cooldownUntil = Number(storedValue)

    return Number.isFinite(cooldownUntil) && cooldownUntil > Date.now() ? cooldownUntil : 0
  } catch {
    return 0
  }
}

function setEmailVerificationCooldown(userId, cooldownUntil) {
  if (!userId) {
    return
  }

  try {
    window.localStorage.setItem(
      getEmailVerificationCooldownKey(userId),
      String(cooldownUntil),
    )
  } catch {
    // Local storage is best-effort; Firebase still enforces the real limit.
  }
}

function clearEmailVerificationCooldown(userId) {
  if (!userId) {
    return
  }

  try {
    window.localStorage.removeItem(getEmailVerificationCooldownKey(userId))
  } catch {
    // Ignore private browsing/storage failures.
  }
}

function getRemainingCooldownSeconds(cooldownUntil) {
  return Math.max(Math.ceil((cooldownUntil - Date.now()) / 1000), 0)
}

export default CreateGamePage
