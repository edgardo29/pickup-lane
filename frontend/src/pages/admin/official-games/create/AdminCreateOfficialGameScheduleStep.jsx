import {
  AdminCreateCurrencyInput,
  AdminCreateField,
  AdminCreateStepHeading,
} from './AdminCreateOfficialGameControls.jsx'
import {
  adminOfficialEnvironmentOptions,
  adminOfficialFormatOptions,
  adminOfficialMaxTotalSpots,
  adminOfficialMinTotalSpots,
  adminOfficialPlayerGroupOptions,
  adminOfficialSkillLevelOptions,
  adminOfficialTimeOptions,
  clampDate,
  getTodayDate,
} from './adminCreateOfficialGameData.js'
import { getMinimumAdminOfficialSpots } from './adminCreateOfficialGameValidation.js'

function AdminCreateOfficialGameScheduleStep({ form, updateField }) {
  const hasSelectedFormat = Boolean(form.formatLabel)
  const minimumSpots = hasSelectedFormat
    ? getMinimumAdminOfficialSpots(form.formatLabel)
    : adminOfficialMinTotalSpots
  const totalSpotOptions = Array.from(
    { length: adminOfficialMaxTotalSpots - minimumSpots + 1 },
    (_, index) => minimumSpots + index,
  )

  function handleFormatChange(nextFormat) {
    updateField('formatLabel', nextFormat)

    if (!nextFormat) {
      return
    }

    const nextMinimumSpots = getMinimumAdminOfficialSpots(nextFormat)
    if (!form.totalSpots || Number(form.totalSpots) < nextMinimumSpots) {
      updateField('totalSpots', nextMinimumSpots)
    }
  }

  return (
    <>
      <AdminCreateStepHeading
        title="Let's start with the game"
        text="Set the schedule, player group, skill level, and price."
      />

      <div className="admin-create-grid admin-create-grid--basics">
        <AdminCreateField label="Date">
          <input
            min={getTodayDate()}
            type="date"
            value={form.date}
            onChange={(event) => updateField('date', clampDate(event.target.value))}
          />
        </AdminCreateField>
        <AdminCreateField label="Start time">
          <select
            aria-label="Start time"
            value={form.startTime}
            onChange={(event) => updateField('startTime', event.target.value)}
          >
            {adminOfficialTimeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="End time">
          <select
            aria-label="End time"
            value={form.endTime}
            onChange={(event) => updateField('endTime', event.target.value)}
          >
            {adminOfficialTimeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="Format">
          <select
            aria-label="Format"
            value={form.formatLabel}
            onChange={(event) => handleFormatChange(event.target.value)}
          >
            <option value="">Select</option>
            {adminOfficialFormatOptions.map((format) => (
              <option key={format} value={format}>
                {format}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="Player group">
          <select
            aria-label="Player group"
            value={form.gamePlayerGroup}
            onChange={(event) => updateField('gamePlayerGroup', event.target.value)}
          >
            <option value="">Select</option>
            {adminOfficialPlayerGroupOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="Skill level">
          <select
            aria-label="Skill level"
            value={form.skillLevel}
            onChange={(event) => updateField('skillLevel', event.target.value)}
          >
            <option value="">Select</option>
            {adminOfficialSkillLevelOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="Indoor/Outdoor">
          <select
            aria-label="Indoor or outdoor"
            value={form.environmentType}
            onChange={(event) => updateField('environmentType', event.target.value)}
          >
            <option value="">Select</option>
            {adminOfficialEnvironmentOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="Total spots">
          <select
            aria-label="Total spots"
            value={form.totalSpots || ''}
            onChange={(event) => (
              updateField('totalSpots', event.target.value ? Number(event.target.value) : '')
            )}
          >
            <option value="">Select</option>
            {totalSpotOptions.map((spots) => (
              <option key={spots} value={spots}>
                {spots}
              </option>
            ))}
          </select>
        </AdminCreateField>
        <AdminCreateField label="Price per player">
          <AdminCreateCurrencyInput
            value={form.price}
            onChange={(value) => updateField('price', value)}
          />
        </AdminCreateField>
      </div>
    </>
  )
}

export default AdminCreateOfficialGameScheduleStep
