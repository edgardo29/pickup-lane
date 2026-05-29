import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  DollarIcon,
  UsersIcon,
} from '../../components/BrowseIcons.jsx'
import {
  CurrencyInput,
  FormField,
  SectionLabel,
  StepHeading,
} from './CreateGameControls.jsx'
import {
  environmentOptions,
  formatOptions,
  MAX_TOTAL_SPOTS,
  timeOptions,
} from './createGameData.js'
import { clampDate, getTodayDate } from './createGameSchedule.js'
import { getMinimumSpotsForFormat } from './createGameValidation.js'

export function BasicsStep({ form, updateField }) {
  const minimumSpots = getMinimumSpotsForFormat(form.format)
  const totalSpotOptions = Array.from(
    { length: MAX_TOTAL_SPOTS - minimumSpots + 1 },
    (_, index) => minimumSpots + index,
  )

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
        <div className="create-game-grid create-game-grid--when">
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
        <SectionLabel>Game Details</SectionLabel>
        <div className="create-game-grid create-game-grid--four">
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
          <FormField icon={<UsersIcon />} label="Total spots">
            <select
              aria-label="Total spots"
              value={form.totalSpots}
              onChange={(event) => updateField('totalSpots', Number(event.target.value))}
            >
              {totalSpotOptions.map((spots) => (
                <option key={spots} value={spots}>
                  {spots}
                </option>
              ))}
            </select>
          </FormField>
          <FormField icon={<DollarIcon />} label="Price per player">
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
