import { useEffect, useMemo, useState } from 'react'
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
  buildAddress,
  buildCommunityGameDetailPayload,
  buildDateTime,
  buildReview,
  cleanNullable,
  COMMUNITY_PUBLISH_FEE_CENTS,
  getExitPath,
  getPaymentCollectionType,
  getHostGuestMaxForFormat,
  getPriceCents,
  initialForm,
  loadEditableGame,
  loadHostPublishFees,
  mapGameToForm,
  patchJson,
  postJson,
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
  const [showDiscardModal, setShowDiscardModal] = useState(false)

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

          refreshBlockedHost()
          return
        }

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

  const review = useMemo(() => buildReview(form), [form])
  const hasUnsavedChanges = useMemo(
    () => JSON.stringify(form) !== JSON.stringify(formBaseline),
    [form, formBaseline],
  )
  const visibleUser = currentUser || appUser
  const isWaitingForUser = isLoading && !visibleUser
  const isHostEmailVerified = Boolean(visibleUser?.email_verified_at)
  const shouldBlockForEmailVerification = visibleUser && !isEditMode && !isHostEmailVerified

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
      const priceCents = getPriceCents(form)

      if (isEditMode) {
        await patchJson(`/games/${gameId}/host-edit`, {
          acting_user_id: currentUser.id,
          starts_at: buildDateTime(form.date, form.startTime),
          ends_at: buildDateTime(form.date, form.endTime),
          format_label: form.format,
          environment_type: form.environment,
          total_spots: Number(form.totalSpots),
          price_per_player_cents: priceCents,
          venue_name: form.venueName.trim(),
          address_line_1: form.street.trim(),
          city: form.city.trim(),
          state: form.state.trim(),
          postal_code: form.zip.trim(),
          neighborhood: form.neighborhood.trim() || null,
          game_notes: form.gameNotes.trim() || null,
          parking_notes: form.parkingNote.trim() || null,
        })

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

      if (!firstPublishIsFree && !paymentMethod) {
        throw new Error('Add a saved payment method before paying the community publish fee.')
      }

      const venue = await postJson('/venues', {
        name: form.venueName.trim(),
        address_line_1: form.street.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
        postal_code: form.zip.trim(),
        country_code: 'US',
        neighborhood: form.neighborhood.trim() || null,
        venue_status: 'approved',
        created_by_user_id: currentUser.id,
        approved_by_user_id: currentUser.id,
        is_active: true,
      })

      const game = await postJson('/games', {
        game_type: 'community',
        payment_collection_type: getPaymentCollectionType(form),
        publish_status: 'published',
        game_status: 'scheduled',
        title: `${form.venueName.trim()} ${form.format}`,
        description: cleanNullable(form.gameNotes),
        venue_id: venue.id,
        venue_name_snapshot: venue.name,
        address_snapshot: buildAddress(form),
        city_snapshot: venue.city,
        state_snapshot: venue.state,
        neighborhood_snapshot: venue.neighborhood,
        host_user_id: currentUser.id,
        created_by_user_id: currentUser.id,
        starts_at: buildDateTime(form.date, form.startTime),
        ends_at: buildDateTime(form.date, form.endTime),
        timezone: 'America/Chicago',
        sport_type: 'soccer',
        format_label: form.format,
        environment_type: form.environment,
        total_spots: Number(form.totalSpots),
        price_per_player_cents: priceCents,
        currency: 'USD',
        minimum_age: 18,
        allow_guests: true,
        max_guests_per_booking: 2,
        host_guest_max: getHostGuestMaxForFormat(form.format),
        waitlist_enabled: true,
        is_chat_enabled: true,
        policy_mode: 'custom_hosted',
        game_notes: form.gameNotes.trim() || null,
        parking_notes: form.parkingNote.trim() || null,
      })

      await postJson('/game-participants', {
        game_id: game.id,
        participant_type: 'host',
        user_id: currentUser.id,
        display_name_snapshot: `${currentUser.first_name} ${currentUser.last_name}`,
        participant_status: 'confirmed',
        attendance_status: 'unknown',
        cancellation_type: 'none',
        price_cents: 0,
        currency: 'USD',
        roster_order: 1,
      })

      await postJson('/community-game-details', buildCommunityGameDetailPayload(form, game.id))

      let payment = null
      if (!firstPublishIsFree) {
        payment = await postJson('/payments', {
          payer_user_id: currentUser.id,
          game_id: game.id,
          payment_type: 'community_publish_fee',
          provider: 'stripe',
          provider_payment_intent_id: `pi_demo_community_publish_fee_${game.id}`,
          provider_charge_id: `ch_demo_community_publish_fee_${game.id}`,
          idempotency_key: `community-publish-fee:${game.id}:${currentUser.id}`,
          amount_cents: COMMUNITY_PUBLISH_FEE_CENTS,
          currency: 'USD',
          payment_status: 'succeeded',
          metadata: {
            source: 'create_game_mock',
            payment_method_id: paymentMethod?.id || null,
          },
        })
      }

      await postJson('/host-publish-fees', {
        game_id: game.id,
        host_user_id: currentUser.id,
        payment_id: payment?.id || null,
        amount_cents: firstPublishIsFree ? 0 : COMMUNITY_PUBLISH_FEE_CENTS,
        currency: 'USD',
        fee_status: firstPublishIsFree ? 'waived' : 'paid',
        waiver_reason: firstPublishIsFree ? 'first_game_free' : 'none',
      })

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
                  paymentMethod={paymentMethod}
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
              paymentMethod={paymentMethod}
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
    setVerificationError('')
    setVerificationNotice('')
    setVerificationStatus('sending')

    try {
      await sendCurrentUserVerificationEmail()
      setVerificationStatus('sent')
    } catch (error) {
      setVerificationError(error instanceof Error ? error.message : 'Unable to send verification email.')
      setVerificationStatus('idle')
    }
  }

}

function EmailVerificationBlocker({ error, notice, onSend, status }) {
  const isSending = status === 'sending'

  return (
    <section className="create-game-blocker">
      <div>
        <p>{status === 'sent' ? 'Email verification sent' : 'Email verification required'}</p>
        <h2>{status === 'sent' ? 'Check your email to continue.' : 'Verify your email to become a host.'}</h2>
        <span>
          {status === 'sent'
            ? 'We sent a verification link to your account email. Check your inbox and spam folder. If it doesn’t show up, wait a minute before resending.'
            : 'Before you can publish a community game, we need to confirm your email address. This helps keep host accounts real and protects players from fake listings.'}
        </span>
      </div>
      <div className="create-game-blocker__actions">
        <button className="create-game-primary" disabled={isSending} type="button" onClick={onSend}>
          {isSending
            ? 'Sending...'
            : status === 'sent'
              ? 'Resend verification email'
              : 'Send verification email'}
        </button>
        {notice && <strong className="create-game-blocker__notice">{notice}</strong>}
        {error && <strong className="create-game-blocker__error">{error}</strong>}
      </div>
    </section>
  )
}

export default CreateGamePage
