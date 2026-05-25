import { useMemo, useState } from 'react'
import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  MapPinIcon,
  PriceTagIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import { timeOptions } from '../../../create-game/createGameData.js'
import { getMinimumSpotsForFormat } from '../../../create-game/createGameValidation.js'
import {
  buildAdminOfficialGamePayload,
  getAdminOfficialGameFormValues,
  officialGameEnvironmentOptions,
  officialGameFormatOptions,
} from './adminOfficialGameForm.js'

function Field({ children, label }) {
  return (
    <label className="admin-official-field-card">
      <span>{label}</span>
      {children}
    </label>
  )
}

function Toggle({ checked, label, onChange }) {
  return (
    <label className="admin-official-check-field">
      <input checked={checked} type="checkbox" onChange={onChange} />
      <span aria-hidden="true" />
      <strong>{label}</strong>
    </label>
  )
}

function StepperInput({ ariaLabel, value, min, max, onChange }) {
  const numericValue = Number(value) || min

  function updateValue(nextValue) {
    onChange(Math.min(Math.max(nextValue, min), max))
  }

  return (
    <div className="admin-official-stepper">
      <button type="button" aria-label={`Decrease ${ariaLabel}`} onClick={() => updateValue(numericValue - 1)}>
        -
      </button>
      <strong>{numericValue}</strong>
      <button type="button" aria-label={`Increase ${ariaLabel}`} onClick={() => updateValue(numericValue + 1)}>
        +
      </button>
    </div>
  )
}

function CurrencyInput({ value, onChange }) {
  function sanitizeMoney(nextValue) {
    const normalized = String(nextValue).replace(/[^\d.]/g, '')
    const [dollars = '', ...centParts] = normalized.split('.')
    const trimmedDollars = dollars.slice(0, 3)
    const cents = centParts.join('').slice(0, 2)
    onChange(cents ? `${trimmedDollars || '0'}.${cents}` : trimmedDollars)
  }

  return (
    <div className="admin-official-money-input">
      <span>$</span>
      <input
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(event) => sanitizeMoney(event.target.value)}
      />
    </div>
  )
}

function TextareaField({ field, form, label, maxLength, placeholder, updateField }) {
  return (
    <label className="admin-official-textarea-field">
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

function buildVenueOptions(venues, game) {
  if (!game?.venue_id || venues.some((venue) => venue.id === game.venue_id)) {
    return venues
  }

  return [
    ...venues,
    {
      id: game.venue_id,
      name: game.venue_name_snapshot,
      address_line_1: game.address_snapshot,
      city: game.city_snapshot,
      state: game.state_snapshot,
    },
  ]
}

function AdminOfficialGameForm({
  game = null,
  isSaving,
  onSubmit,
  submitLabel,
  venues = [],
}) {
  const [form, setForm] = useState(() => getAdminOfficialGameFormValues(game))
  const [formError, setFormError] = useState('')
  const venueOptions = useMemo(() => buildVenueOptions(venues, game), [game, venues])

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    setFormError('')

    try {
      onSubmit(buildAdminOfficialGamePayload(form, venueOptions))
    } catch (error) {
      setFormError(error.message)
    }
  }

  function updateFormat(nextFormat) {
    updateField('formatLabel', nextFormat)

    const minimumSpots = getMinimumSpotsForFormat(nextFormat)
    if (Number(form.totalSpots) < minimumSpots) {
      updateField('totalSpots', minimumSpots)
    }
  }

  const minimumSpots = getMinimumSpotsForFormat(form.formatLabel)
  const venueDisplay = [
    game?.venue_name_snapshot || form.venueName,
    game?.city_snapshot,
    game?.state_snapshot,
  ].filter(Boolean).join(' - ')
  const venueAddress = game?.address_snapshot || ''

  return (
    <form className="admin-official-form" onSubmit={handleSubmit}>
      <div className="admin-official-form__section">
        <div className="admin-official-section-title">
          <SoccerBallIcon />
          <h2>Game</h2>
        </div>

        <div className="admin-official-form__grid admin-official-form__grid--two">
          <Field icon={<UsersIcon />} label="Format">
            <select
              value={form.formatLabel}
              onChange={(event) => updateFormat(event.target.value)}
            >
              {officialGameFormatOptions.map((format) => (
                <option key={format} value={format}>{format}</option>
              ))}
            </select>
          </Field>
          <Field icon={<BuildingIcon />} label="Indoor / Outdoor">
            <select
              value={form.environmentType}
              onChange={(event) => updateField('environmentType', event.target.value)}
            >
              {officialGameEnvironmentOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>
        </div>
      </div>

      <div className="admin-official-form__section">
        <div className="admin-official-section-title">
          <CalendarIcon />
          <h2>Schedule</h2>
        </div>

        <div className="admin-official-form__grid admin-official-form__grid--three">
          <Field icon={<CalendarIcon />} label="Date">
            <input
              required
              type="date"
              value={form.date}
              onChange={(event) => updateField('date', event.target.value)}
            />
          </Field>
          <Field icon={<ClockIcon />} label="Start time">
            <select value={form.startTime} onChange={(event) => updateField('startTime', event.target.value)}>
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
          <Field icon={<ClockIcon />} label="End time">
            <select value={form.endTime} onChange={(event) => updateField('endTime', event.target.value)}>
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </div>

      <div className="admin-official-form__section">
        <div className="admin-official-section-title">
          <UsersIcon />
          <h2>Booking</h2>
        </div>

        <div className="admin-official-form__grid admin-official-form__grid--three">
          <Field icon={<UsersIcon />} label="Total spots">
            <StepperInput
              ariaLabel="total spots"
              value={form.totalSpots}
              min={minimumSpots}
              max={99}
              onChange={(value) => updateField('totalSpots', value)}
            />
          </Field>
          <Field icon={<UsersIcon />} label="Max guests">
            <StepperInput
              ariaLabel="max guests"
              value={form.maxGuestsPerBooking}
              min={0}
              max={2}
              onChange={(value) => updateField('maxGuestsPerBooking', value)}
            />
          </Field>
          <Field icon={<PriceTagIcon />} label="Price per player">
            <CurrencyInput
              value={form.price}
              onChange={(value) => updateField('price', value)}
            />
          </Field>
        </div>

        <div className="admin-official-toggle-row">
          <Toggle
            checked={form.allowGuests}
            label="Guests"
            onChange={(event) => updateField('allowGuests', event.target.checked)}
          />
          <Toggle
            checked={form.waitlistEnabled}
            label="Waitlist"
            onChange={(event) => updateField('waitlistEnabled', event.target.checked)}
          />
          <Toggle
            checked={form.isChatEnabled}
            label="Chat"
            onChange={(event) => updateField('isChatEnabled', event.target.checked)}
          />
        </div>
      </div>

      <div className="admin-official-form__section">
        <div className="admin-official-section-title">
          <MapPinIcon />
          <h2>Location</h2>
        </div>

        <div className="admin-official-readonly-location">
          <strong>{venueDisplay || 'Venue unavailable'}</strong>
          {venueAddress && <span>{venueAddress}</span>}
        </div>
      </div>

      <div className="admin-official-form__section">
        <div className="admin-official-textarea-stack">
          <TextareaField
            field="playerInstructions"
            form={form}
            label="Player instructions"
            maxLength={220}
            placeholder="Optional player instructions"
            updateField={updateField}
          />
          <TextareaField
            field="parkingNotes"
            form={form}
            label="Parking note"
            maxLength={160}
            placeholder="Parking or arrival details"
            updateField={updateField}
          />
        </div>
      </div>

      {(formError) && <p className="admin-official-form__error">{formError}</p>}

      <div className="admin-official-form__actions">
        <button className="admin-official-button admin-official-button--primary" disabled={isSaving} type="submit">
          <span>{isSaving ? 'Saving' : submitLabel}</span>
        </button>
      </div>
    </form>
  )
}

export default AdminOfficialGameForm
