import { Link, useNavigate, useParams } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { ArrowLeftIcon, InfoIcon, ShieldCheckIcon } from '../components/AuthIcons.jsx'
import BrowseAppNav from '../components/BrowseAppNav.jsx'
import {
  BuildingIcon,
  CalendarIcon,
  ChatIcon,
  ClockIcon,
  MapPinIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../components/BrowseIcons.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { apiRequest } from '../lib/apiClient.js'
import '../styles/create-game.css'

const HOST_DEPOSIT_CENTS = 1000
const formatOptions = ['3v3', '4v4', '5v5', '6v6', '7v7', '8v8', '9v9', '10v10', '11v11']
const environmentOptions = [
  { label: 'Indoor', value: 'indoor' },
  { label: 'Outdoor', value: 'outdoor' },
]

const initialForm = {
  date: getDefaultDate(),
  startTime: '18:00',
  endTime: '20:00',
  format: '7v7',
  environment: 'outdoor',
  totalSpots: 14,
  price: 25,
  venueName: '',
  street: '',
  city: '',
  state: '',
  zip: '',
  neighborhood: '',
  arrivalNote: '',
  parkingNote: '',
  gameNotes: '',
}

const steps = [
  { id: 1, label: 'Basics' },
  { id: 2, label: 'Location' },
  { id: 3, label: 'Notes' },
  { id: 4, label: 'Review & Publish' },
]

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
          arrival_notes: form.arrivalNote.trim() || null,
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

      const startsAt = buildDateTime(form.date, form.startTime)
      const endsAt = buildDateTime(form.date, form.endTime)
      const title = `${form.venueName.trim()} ${form.format}`
      const game = await postJson('/games', {
        game_type: 'community',
        publish_status: 'published',
        game_status: 'scheduled',
        title,
        description: form.gameNotes || null,
        venue_id: venue.id,
        venue_name_snapshot: venue.name,
        address_snapshot: buildAddress(form),
        city_snapshot: venue.city,
        state_snapshot: venue.state,
        neighborhood_snapshot: venue.neighborhood,
        host_user_id: currentUser.id,
        created_by_user_id: currentUser.id,
        starts_at: startsAt,
        ends_at: endsAt,
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
        arrival_notes: form.arrivalNote.trim() || null,
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

function StepRail({ activeStep }) {
  return (
    <ol className="create-game-steps" aria-label="Create game progress">
      {steps.map((step) => (
        <li
          className={step.id === activeStep ? 'active' : step.id < activeStep ? 'complete' : ''}
          key={step.id}
        >
          <span>{step.id}</span>
          <strong>{step.label}</strong>
        </li>
      ))}
    </ol>
  )
}

function BasicsStep({ form, updateField }) {
  return (
    <>
      <StepHeading
        title="Let's start with the basics"
        text="Tell players when and what kind of game you're hosting."
      />

      <div className="create-game-section">
        <SectionLabel>When</SectionLabel>
        <div className="create-game-grid">
          <FormField icon={<CalendarIcon />} label="Date">
            <input
              value={form.date}
              min={getTodayDate()}
              type="date"
              onChange={(event) => updateField('date', clampDate(event.target.value))}
            />
          </FormField>
          <FormField icon={<ClockIcon />} label="Start time">
            <input
              value={form.startTime}
              type="time"
              onChange={(event) => updateField('startTime', event.target.value)}
            />
          </FormField>
          <FormField icon={<ClockIcon />} label="End time">
            <input
              value={form.endTime}
              type="time"
              onChange={(event) => updateField('endTime', event.target.value)}
            />
          </FormField>
        </div>
      </div>

      <div className="create-game-section">
        <SectionLabel>Game Setup</SectionLabel>
        <div className="create-game-grid">
          <FormField icon={<UsersIcon />} label="Format">
            <select
              aria-label="Format"
              value={form.format}
              onChange={(event) => updateField('format', event.target.value)}
            >
              {formatOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </FormField>
          <FormField icon={<BuildingIcon />} label="Indoor / Outdoor">
            <select
              aria-label="Indoor or outdoor"
              value={form.environment}
              onChange={(event) => updateField('environment', event.target.value)}
            >
              {environmentOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
        </div>
      </div>

      <div className="create-game-section">
        <SectionLabel>Spots & Price</SectionLabel>
        <div className="create-game-grid">
          <FormField icon={<UsersIcon />} label="Total spots">
            <StepperInput
              value={form.totalSpots}
              min={2}
              max={30}
              onChange={(value) => updateField('totalSpots', value)}
            />
          </FormField>
          <FormField icon={<SoccerBallIcon />} label="Price per player">
            <CurrencyInput
              value={form.price}
              onChange={(value) => updateField('price', value)}
            />
          </FormField>
        </div>
      </div>
    </>
  )
}

function LocationStep({ form, updateField }) {
  return (
    <>
      <StepHeading
        title="Where will you play?"
        text="Add the venue details players will see on the game page."
      />

      <div className="create-game-grid create-game-grid--single">
        <TextInput
          form={form}
          updateField={updateField}
          field="venueName"
          label="Venue name"
          placeholder="e.g. Brooklyn Sports Hub"
        />
        <TextInput
          form={form}
          updateField={updateField}
          field="street"
          label="Street address"
          placeholder="160 5th St"
        />
      </div>

      <div className="create-game-grid create-game-grid--two">
        <TextInput form={form} updateField={updateField} field="city" label="City" placeholder="Brooklyn" />
        <TextInput form={form} updateField={updateField} field="state" label="State" placeholder="New York" />
        <TextInput form={form} updateField={updateField} field="zip" label="ZIP code" placeholder="11215" />
        <TextInput
          form={form}
          updateField={updateField}
          field="neighborhood"
          label="Neighborhood"
          placeholder="Park Slope"
        />
      </div>

      <div className="create-game-divider" />

      <TextareaInput
        form={form}
        updateField={updateField}
        field="arrivalNote"
        label="Arrival note"
        maxLength={120}
        placeholder="Help players find the entrance, check in, etc."
      />
      <TextareaInput
        form={form}
        updateField={updateField}
        field="parkingNote"
        label="Parking note"
        maxLength={120}
        placeholder="Share parking info or nearby options."
      />
    </>
  )
}

function NotesStep({ form, updateField }) {
  return (
    <>
      <StepHeading
        title="Anything players should know?"
        text="Add a short note that will appear on the game page."
      />

      <TextareaInput
        form={form}
        updateField={updateField}
        field="gameNotes"
        label="Game notes"
        maxLength={200}
        placeholder="Share any important info with players..."
      />

      <p className="create-game-note">
        <InfoIcon />
        Keep it short and helpful. This will be visible to all players.
      </p>
    </>
  )
}

function ReviewStep({ form, isEditMode, paymentMethod, publishError, review }) {
  return (
    <>
      <StepHeading
        title={isEditMode ? 'Review your changes' : 'Review your game'}
        text={
          isEditMode
            ? 'Confirm your updates before saving this community game.'
            : 'Confirm your details before publishing your community game.'
        }
      />

      <div className="create-game-review-card">
        <ReviewRow icon={<CalendarIcon />} label="Date" value={review.date} />
        <ReviewRow icon={<ClockIcon />} label="Time" value={review.time} />
        <ReviewRow icon={<UsersIcon />} label="Format" value={form.format} />
        <ReviewRow
          icon={<BuildingIcon />}
          label="Indoor / Outdoor"
          value={capitalize(form.environment)}
        />
        <ReviewRow icon={<UsersIcon />} label="Total spots" value={`${form.totalSpots} players`} />
        <ReviewRow icon={<SoccerBallIcon />} label="Price per player" value={formatMoney(Number(form.price) * 100)} />
        <hr />
        <ReviewRow icon={<MapPinIcon />} label="Venue" value={form.venueName || 'Not added'} />
        <ReviewRow icon={<MapPinIcon />} label="Address" value={buildAddress(form) || 'Not added'} />
        <hr />
        <ReviewRow icon={<ChatIcon />} label="Game notes" value={form.gameNotes || 'No notes added.'} />
      </div>

      {!isEditMode && (
        <>
          <div className="create-game-deposit-card">
            <ShieldCheckIcon />
            <div>
              <span>Refundable host deposit</span>
              <strong>{formatMoney(HOST_DEPOSIT_CENTS)}</strong>
              <p>Held after publishing. Released after the game is successfully hosted.</p>
            </div>
          </div>

          <div className="create-game-payment-row">
            <span>Payment method</span>
            <strong>{formatPaymentMethod(paymentMethod)}</strong>
          </div>

          <div className="create-game-total-row">
            <span>Deposit due today</span>
            <strong>{formatMoney(HOST_DEPOSIT_CENTS)}</strong>
          </div>
        </>
      )}

      {publishError && <p className="create-game-error">{publishError}</p>}
    </>
  )
}

function CreateGamePreview({ form, paymentMethod, review }) {
  return (
    <aside className="create-game-preview" aria-label="Game preview">
      <div className="create-game-preview__header">
        <span>Live preview</span>
        <strong>{form.venueName ? `${form.venueName} ${form.format}` : `Community ${form.format}`}</strong>
      </div>

      <div className="create-game-preview__facts">
        <PreviewFact icon={<CalendarIcon />} label={review.date} />
        <PreviewFact icon={<ClockIcon />} label={review.time} />
        <PreviewFact icon={<MapPinIcon />} label={buildPreviewLocation(form)} />
        <PreviewFact icon={<UsersIcon />} label={`${form.totalSpots} spots · ${form.format}`} />
        <PreviewFact icon={<BuildingIcon />} label={capitalize(form.environment)} />
      </div>

      <div className="create-game-preview__money">
        <span>Player price</span>
        <strong>{formatMoney(Number(form.price) * 100)}</strong>
      </div>

      <div className="create-game-preview__money">
        <span>Host deposit</span>
        <strong>{formatMoney(HOST_DEPOSIT_CENTS)}</strong>
      </div>

      <p className="create-game-preview__note">
        {form.gameNotes || 'Add a note so players know what to bring.'}
      </p>

      <p className="create-game-preview__card">Paying with {formatPaymentMethod(paymentMethod)}</p>
    </aside>
  )
}

function PublishedState({ gameId }) {
  return (
    <div className="create-game-page">
      <BrowseAppNav />
      <main className="create-game-success">
        <div className="create-game-success__mark">
          <ShieldCheckIcon />
        </div>
        <h1>Game Published!</h1>
        <p>Your community game is now live and visible to players.</p>
        <Link className="create-game-primary" to={`/games/${gameId}`}>
          View Game
          <span aria-hidden="true">→</span>
        </Link>
      </main>
    </div>
  )
}

function StepHeading({ title, text }) {
  return (
    <div className="create-game-heading">
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  )
}

function SectionLabel({ children }) {
  return <h3 className="create-game-section-label">{children}</h3>
}

function FormField({ icon, label, children }) {
  return (
    <div className="create-game-field">
      {icon}
      <span>{label}</span>
      {children}
    </div>
  )
}

function TextInput({ form, updateField, field, label, placeholder }) {
  return (
    <label className="create-game-text-field">
      <span>{label}</span>
      <input
        placeholder={placeholder}
        value={form[field]}
        onChange={(event) => updateField(field, event.target.value)}
      />
    </label>
  )
}

function StepperInput({ value, min, max, onChange }) {
  const numericValue = Number(value) || min

  function updateValue(nextValue) {
    onChange(Math.min(Math.max(nextValue, min), max))
  }

  return (
    <div className="create-game-stepper">
      <button type="button" onClick={() => updateValue(numericValue - 1)} aria-label="Decrease total spots">
        −
      </button>
      <strong>{numericValue}</strong>
      <button type="button" onClick={() => updateValue(numericValue + 1)} aria-label="Increase total spots">
        +
      </button>
    </div>
  )
}

function CurrencyInput({ value, onChange }) {
  return (
    <div className="create-game-money-input">
      <span>$</span>
      <input
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => onChange(sanitizeMoney(event.target.value))}
      />
    </div>
  )
}

function TextareaInput({ form, updateField, field, label, maxLength, placeholder }) {
  return (
    <label className="create-game-textarea-field">
      <span>{label}</span>
      <textarea
        maxLength={maxLength}
        placeholder={placeholder}
        value={form[field]}
        onChange={(event) => updateField(field, event.target.value)}
      />
      <small>{form[field].length}/{maxLength}</small>
    </label>
  )
}

function ReviewRow({ icon, label, value }) {
  return (
    <div className="create-game-review-row">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function PreviewFact({ icon, label }) {
  return (
    <span>
      {icon}
      {label}
    </span>
  )
}

function DiscardModal({ onClose, onDiscard }) {
  return (
    <div className="create-game-modal-backdrop" role="presentation">
      <div className="create-game-modal" role="dialog" aria-modal="true" aria-labelledby="discard-game-title">
        <h2 id="discard-game-title">Discard game?</h2>
        <p>Your game has not been published. Any details you entered will be lost.</p>
        <div className="create-game-modal__actions">
          <button type="button" className="create-game-secondary" onClick={onClose}>
            Keep editing
          </button>
          <button type="button" className="create-game-danger" onClick={onDiscard}>
            Discard
          </button>
        </div>
      </div>
    </div>
  )
}

async function postJson(path, payload) {
  return apiRequest(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

async function patchJson(path, payload) {
  return apiRequest(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

async function loadEditableGame(gameId) {
  const game = await apiRequest(`/games/${gameId}`)
  const venue = await apiRequest(`/venues/${game.venue_id}`).catch(() => null)
  return { game, venue }
}

function mapGameToForm(game, venue) {
  const startsAt = new Date(game.starts_at)
  const endsAt = new Date(game.ends_at)

  return {
    date: toDateInputValue(startsAt),
    startTime: toTimeInputValue(startsAt),
    endTime: toTimeInputValue(endsAt),
    format: game.format_label || '7v7',
    environment: game.environment_type || 'outdoor',
    totalSpots: game.total_spots || 14,
    price: Math.round((game.price_per_player_cents || 0) / 100),
    venueName: venue?.name || game.venue_name_snapshot || '',
    street: venue?.address_line_1 || getStreetFromAddressSnapshot(game.address_snapshot),
    city: venue?.city || game.city_snapshot || '',
    state: venue?.state || game.state_snapshot || '',
    zip: venue?.postal_code || '',
    neighborhood: venue?.neighborhood || game.neighborhood_snapshot || '',
    arrivalNote: game.arrival_notes || '',
    parkingNote: game.parking_notes || '',
    gameNotes: game.game_notes || '',
  }
}

function buildReview(form) {
  return {
    date: new Intl.DateTimeFormat('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(new Date(`${form.date}T12:00:00`)),
    time: `${formatTime(form.startTime)} – ${formatTime(form.endTime)}`,
  }
}

function buildDateTime(date, time) {
  return new Date(`${date}T${time}:00`).toISOString()
}

function buildAddress(form) {
  const stateLine = [form.state.trim(), form.zip.trim()].filter(Boolean).join(' ')
  const cityLine = [form.city.trim(), stateLine].filter(Boolean).join(', ')
  return [form.street.trim(), cityLine].filter(Boolean).join(', ')
}

function buildPreviewLocation(form) {
  return form.neighborhood || form.city || form.state || 'Location not set'
}

function getExitPath(isEditMode, gameId) {
  return isEditMode && gameId ? `/games/${gameId}` : '/my-games'
}

function validateStep(step, form) {
  if (step === 1) {
    if (form.date < getTodayDate()) {
      return 'Choose today or a future date.'
    }

    if (form.endTime <= form.startTime) {
      return 'End time must be after the start time.'
    }
  }

  if (step === 2) {
    const requiredFields = [
      ['venueName', 'venue name'],
      ['street', 'street address'],
      ['city', 'city'],
      ['state', 'state'],
      ['zip', 'ZIP code'],
    ]
    const missingField = requiredFields.find(([field]) => !form[field].trim())

    if (missingField) {
      return `Add a ${missingField[1]} before continuing.`
    }
  }

  return ''
}

function validateCreateGame(form) {
  for (const step of [1, 2]) {
    const message = validateStep(step, form)
    if (message) {
      return { step, message }
    }
  }

  return null
}

function clampDate(value) {
  if (!value) {
    return getTodayDate()
  }

  return value < getTodayDate() ? getTodayDate() : value
}

function sanitizeMoney(value) {
  const digitsOnly = value.replace(/[^\d]/g, '')
  if (!digitsOnly) {
    return 0
  }

  return Math.min(Number(digitsOnly), 999)
}

function formatPaymentMethod(paymentMethod) {
  if (!paymentMethod) {
    return 'Visa •••• 4242'
  }

  return `${capitalize(paymentMethod.card_brand || 'card')} •••• ${paymentMethod.card_last4}`
}

function formatTime(value) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(`2026-01-01T${value}:00`))
}

function formatMoney(cents) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format((cents || 0) / 100)
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : ''
}

function getDefaultDate() {
  const date = new Date()
  date.setDate(date.getDate() + 10)
  return toDateInputValue(date)
}

function getTodayDate() {
  return toDateInputValue(new Date())
}

function toDateInputValue(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function toTimeInputValue(date) {
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

function getStreetFromAddressSnapshot(addressSnapshot) {
  return addressSnapshot?.split(',')[0]?.trim() || ''
}

export default CreateGamePage
