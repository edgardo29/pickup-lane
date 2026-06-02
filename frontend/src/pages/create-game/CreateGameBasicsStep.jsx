import {
  CurrencyInput,
  FormField,
  StepHeading,
} from './CreateGameControls.jsx'
import {
  environmentOptions,
  formatOptions,
  MAX_TOTAL_SPOTS,
  MINIMUM_TOTAL_SPOTS,
  playerGroupOptions,
  skillLevelOptions,
  timeOptions,
} from './createGameData.js'
import { clampDate, getTodayDate } from './createGameSchedule.js'
import { getMinimumSpotsForFormat } from './createGameValidation.js'

export function BasicsStep({ form, updateField }) {
  const hasSelectedFormat = Boolean(form.format)
  const minimumSpots = hasSelectedFormat ? getMinimumSpotsForFormat(form.format) : MINIMUM_TOTAL_SPOTS
  const totalSpotOptions = Array.from(
    { length: MAX_TOTAL_SPOTS - minimumSpots + 1 },
    (_, index) => minimumSpots + index,
  )

  function handleFormatChange(nextFormat) {
    updateField('format', nextFormat)

    if (!nextFormat) {
      return
    }

    const nextMinimumSpots = getMinimumSpotsForFormat(nextFormat)
    if (!form.totalSpots || Number(form.totalSpots) < nextMinimumSpots) {
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
        title="Let's start with the game"
        text="Set the schedule, player group, skill level, and price."
      />

      <div className="create-game-section">
        <div className="create-game-grid create-game-grid--basics">
          <FormField label="Date">
            <input
              value={form.date}
              min={getTodayDate()}
              type="date"
              onChange={(event) => updateField('date', clampDate(event.target.value))}
            />
          </FormField>
          <FormField label="Start time">
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
          <FormField label="End time">
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
          <FormField label="Format">
            <select
              aria-label="Format"
              value={form.format}
              onChange={(event) => handleFormatChange(event.target.value)}
            >
              <option value="">Select</option>
              {formatOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Player group">
            <select
              aria-label="Player group"
              value={form.gamePlayerGroup}
              onChange={(event) => updateField('gamePlayerGroup', event.target.value)}
            >
              <option value="">Select</option>
              {playerGroupOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Skill level">
            <select
              aria-label="Skill level"
              value={form.skillLevel}
              onChange={(event) => updateField('skillLevel', event.target.value)}
            >
              <option value="">Select</option>
              {skillLevelOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Indoor/Outdoor">
            <select
              aria-label="Indoor or outdoor"
              value={form.environment}
              onChange={(event) => updateField('environment', event.target.value)}
            >
              <option value="">Select</option>
              {environmentOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Total spots">
            <select
              aria-label="Total spots"
              value={form.totalSpots || ''}
              onChange={(event) => updateField('totalSpots', event.target.value ? Number(event.target.value) : '')}
            >
              <option value="">Select</option>
              {totalSpotOptions.map((spots) => (
                <option key={spots} value={spots}>
                  {spots}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Price per player">
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
