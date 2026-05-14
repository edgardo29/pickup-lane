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
  HOST_DEPOSIT_CENTS,
  buildAddress,
  buildDateTime,
  buildReview,
  getExitPath,
  initialForm,
  loadEditableGame,
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
  const { appUser, isLoading } = useAuth()
  const isEditMode = Boolean(gameId)
  const [activeStep, setActiveStep] = useState(1)
  const [form, setForm] = useState(initialForm)
  const [formBaseline, setFormBaseline] = useState(initialForm)
  const [currentUser, setCurrentUser] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState(null)
  const [createdGameId, setCreatedGameId] = useState('')
  const [status, setStatus] = useState('idle')
  const [loadError, setLoadError] = useState('')
  const [publishError, setPublishError] = useState('')
  const [stepError, setStepError] = useState('')
  const [showDiscardModal, setShowDiscardModal] = useState(false)

  useEffect(() => {
    let ignore = false

    async function loadCreateGameContext() {
      try {
        if (isLoading) {
          return
        }

        if (!appUser?.id) {
          throw new Error('Sign in to create a game.')
        }

        const [paymentMethods, gameContext] = await Promise.all([
          apiRequest(`/user-payment-methods?user_id=${appUser.id}`),
          isEditMode ? loadEditableGame(gameId) : Promise.resolve(null),
        ])

        if (!ignore) {
          setCurrentUser(appUser)
          setPaymentMethod(paymentMethods.find((method) => method.is_default) || paymentMethods[0] || null)

          if (gameContext) {
            const editableForm = mapGameToForm(gameContext.game, gameContext.venue)
            setForm(editableForm)
            setFormBaseline(editableForm)
          }
        }
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
  }, [appUser, gameId, isEditMode, isLoading])

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
        await patchJson(`/games/${gameId}/host-edit`, {
          acting_user_id: currentUser.id,
          starts_at: buildDateTime(form.date, form.startTime),
          ends_at: buildDateTime(form.date, form.endTime),
          format_label: form.format,
          environment_type: form.environment,
          total_spots: Number(form.totalSpots),
          price_per_player_cents: Number(form.price) * 100,
          venue_name: form.venueName.trim(),
          address_line_1: form.street.trim(),
          city: form.city.trim(),
          state: form.state.trim(),
          postal_code: form.zip.trim(),
          neighborhood: form.neighborhood.trim() || null,
          game_notes: form.gameNotes.trim() || null,
          parking_notes: form.parkingNote.trim() || null,
        })

        navigate(`/games/${gameId}`)
        return
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
        payment_collection_type: priceCents > 0 ? 'external_host' : 'none',
        publish_status: 'published',
        game_status: 'scheduled',
        title: `${form.venueName.trim()} ${form.format}`,
        description: form.gameNotes || null,
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
        price_per_player_cents: Number(form.price) * 100,
        currency: 'USD',
        minimum_age: 18,
        allow_guests: true,
        max_guests_per_booking: 2,
        waitlist_enabled: true,
        is_chat_enabled: true,
        policy_mode: 'custom_hosted',
        custom_rules_text: null,
        custom_cancellation_text: null,
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

      const payment = await postJson('/payments', {
        payer_user_id: currentUser.id,
        game_id: game.id,
        payment_type: 'host_deposit',
        provider: 'stripe',
        provider_payment_intent_id: `pi_demo_host_deposit_${game.id}`,
        provider_charge_id: `ch_demo_host_deposit_${game.id}`,
        idempotency_key: `host-deposit:${game.id}:${currentUser.id}`,
        amount_cents: HOST_DEPOSIT_CENTS,
        currency: 'USD',
        payment_status: 'succeeded',
        metadata: {
          source: 'create_game_mock',
          payment_method_id: paymentMethod?.id || null,
        },
      })

      await postJson('/host-deposits', {
        game_id: game.id,
        host_user_id: currentUser.id,
        required_amount_cents: HOST_DEPOSIT_CENTS,
        currency: 'USD',
        deposit_status: 'held',
        payment_id: payment.id,
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

        <section className="create-game-layout">
          <div className="create-game-panel">
            {activeStep === 1 && <BasicsStep form={form} updateField={updateField} />}
            {activeStep === 2 && <LocationStep form={form} updateField={updateField} />}
            {activeStep === 3 && <NotesStep form={form} updateField={updateField} />}
            {activeStep === 4 && (
              <ReviewStep
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
                {activeStep < 4 ? (
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
                        : 'Pay Deposit & Publish'}
                    <span aria-hidden="true">→</span>
                  </button>
                )}
              </div>
            </div>
          </div>

          <CreateGamePreview form={form} paymentMethod={paymentMethod} review={review} />
        </section>
      </main>

      {showDiscardModal && (
        <DiscardModal onClose={() => setShowDiscardModal(false)} onDiscard={discardGame} />
      )}
    </div>
  )
}

export default CreateGamePage
