import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  SoccerBallIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  CurrencyInput,
  FormField,
  SectionLabel,
  StepHeading,
  StepperInput,
} from './CreateGameControls.jsx'
import {
  environmentOptions,
  formatOptions,
  timeOptions,
} from './createGameData.js'
import { clampDate, getTodayDate } from './createGameSchedule.js'
import { getMinimumSpotsForFormat } from './createGameValidation.js'

export function BasicsStep({ form, updateField }) {
  const minimumSpots = getMinimumSpotsForFormat(form.format)

  function handleFormatChange(nextFormat) {
    updateField('format', nextFormat)

    const nextMinimumSpots = getMinimumSpotsForFormat(nextFormat)
    if (Number(form.totalSpots) < nextMinimumSpots) {
      updateField('totalSpots', nextMinimumSpots)
    }
  }

  function handlePriceChange(nextPrice) {
    updateField('price', nextPrice)

    if (nextPrice === 0) {
      updateField('paymentMethods', [{ type: 'none', value: '' }])
      return
    }

    if (form.paymentMethods.length === 1 && form.paymentMethods[0]?.type === 'none') {
      updateField('paymentMethods', [{ type: 'venmo', value: '' }])
    }
  }

  return (
    <>
      <StepHeading
        title="Let's start with the basics"
        text="Community hosts can create one game per day."
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
              onChange={handlePriceChange}
            />
          </FormField>
        </div>
      </div>
    </>
  )
}
