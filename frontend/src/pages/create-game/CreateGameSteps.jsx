import { InfoIcon, ShieldCheckIcon } from '../../components/AuthIcons.jsx'
import {
  BuildingIcon,
  CalendarIcon,
  ChatIcon,
  ClockIcon,
  MapPinIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  CurrencyInput,
  FormField,
  ReviewRow,
  SectionLabel,
  StepHeading,
  StepperInput,
  TextareaInput,
  TextInput,
} from './CreateGameControls.jsx'
import {
  buildAddress,
  capitalize,
  clampDate,
  environmentOptions,
  formatMoney,
  formatOptions,
  formatPaymentMethod,
  getMinimumSpotsForFormat,
  getTodayDate,
  HOST_DEPOSIT_CENTS,
  steps,
  timeOptions,
} from './createGameUtils.js'

export function StepRail({ activeStep }) {
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

export function BasicsStep({ form, updateField }) {
  const minimumSpots = getMinimumSpotsForFormat(form.format)

  function handleFormatChange(nextFormat) {
    updateField('format', nextFormat)

    const nextMinimumSpots = getMinimumSpotsForFormat(nextFormat)
    if (Number(form.totalSpots) < nextMinimumSpots) {
      updateField('totalSpots', nextMinimumSpots)
    }
  }

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
            <select
              aria-label="Start time"
              value={form.startTime}
              onChange={(event) => updateField('startTime', event.target.value)}
            >
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField icon={<ClockIcon />} label="End time">
            <select
              aria-label="End time"
              value={form.endTime}
              onChange={(event) => updateField('endTime', event.target.value)}
            >
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
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
              onChange={(event) => handleFormatChange(event.target.value)}
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
              min={minimumSpots}
              max={99}
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

export function LocationStep({ form, updateField }) {
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
          label="Neighborhood (optional)"
          placeholder="Park Slope"
        />
      </div>

      <div className="create-game-divider" />

      <TextareaInput
        form={form}
        updateField={updateField}
        field="parkingNote"
        label="Parking note (optional)"
        maxLength={120}
        placeholder="Share parking info or nearby options."
      />
    </>
  )
}

export function NotesStep({ form, updateField }) {
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

export function ReviewStep({ form, isEditMode, paymentMethod, publishError, review }) {
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
