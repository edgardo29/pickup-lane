import {
  BuildingIcon,
  CalendarIcon,
  ClockIcon,
  PriceTagIcon,
  UsersIcon,
} from '../../../../components/BrowseIcons.jsx'
import {
  AdminCreateCurrencyInput,
  AdminCreateField,
  AdminCreateSectionLabel,
  AdminCreateStepperInput,
  AdminCreateStepHeading,
} from './AdminCreateOfficialGameControls.jsx'
import {
  adminOfficialEnvironmentOptions,
  adminOfficialFormatOptions,
  adminOfficialTimeOptions,
  clampDate,
  getTodayDate,
} from './adminCreateOfficialGameData.js'
import { getMinimumAdminOfficialSpots } from './adminCreateOfficialGameValidation.js'

function AdminCreateOfficialGameScheduleStep({ form, updateField }) {
  const minimumSpots = getMinimumAdminOfficialSpots(form.formatLabel)

  function handleFormatChange(nextFormat) {
    updateField('formatLabel', nextFormat)

    const nextMinimumSpots = getMinimumAdminOfficialSpots(nextFormat)
    if (Number(form.totalSpots) < nextMinimumSpots) {
      updateField('totalSpots', nextMinimumSpots)
    }
  }

  return (
    <>
      <AdminCreateStepHeading
        title="Let's start with the basics"
        text="Set the official game schedule, format, roster size, and checkout price."
      />

      <div className="admin-create-section">
        <AdminCreateSectionLabel>When</AdminCreateSectionLabel>
        <div className="admin-create-grid">
          <AdminCreateField icon={<CalendarIcon />} label="Date">
            <input
              min={getTodayDate()}
              type="date"
              value={form.date}
              onChange={(event) => updateField('date', clampDate(event.target.value))}
            />
          </AdminCreateField>
          <AdminCreateField icon={<ClockIcon />} label="Start time">
            <select value={form.startTime} onChange={(event) => updateField('startTime', event.target.value)}>
              {adminOfficialTimeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminCreateField>
          <AdminCreateField icon={<ClockIcon />} label="End time">
            <select value={form.endTime} onChange={(event) => updateField('endTime', event.target.value)}>
              {adminOfficialTimeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminCreateField>
        </div>
      </div>

      <div className="admin-create-section">
        <AdminCreateSectionLabel>Game Setup</AdminCreateSectionLabel>
        <div className="admin-create-grid admin-create-grid--two">
          <AdminCreateField icon={<UsersIcon />} label="Format">
            <select value={form.formatLabel} onChange={(event) => handleFormatChange(event.target.value)}>
              {adminOfficialFormatOptions.map((format) => (
                <option key={format} value={format}>
                  {format}
                </option>
              ))}
            </select>
          </AdminCreateField>
          <AdminCreateField icon={<BuildingIcon />} label="Indoor / Outdoor">
            <select value={form.environmentType} onChange={(event) => updateField('environmentType', event.target.value)}>
              {adminOfficialEnvironmentOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminCreateField>
        </div>
      </div>

      <div className="admin-create-section">
        <AdminCreateSectionLabel>Spots & Price</AdminCreateSectionLabel>
        <div className="admin-create-grid admin-create-grid--two">
          <AdminCreateField icon={<UsersIcon />} label="Total spots">
            <AdminCreateStepperInput
              ariaLabel="total spots"
              value={form.totalSpots}
              min={minimumSpots}
              max={99}
              onChange={(value) => updateField('totalSpots', value)}
            />
          </AdminCreateField>
          <AdminCreateField icon={<PriceTagIcon />} label="Price per player">
            <AdminCreateCurrencyInput
              value={form.price}
              onChange={(value) => updateField('price', value)}
            />
          </AdminCreateField>
        </div>
      </div>
    </>
  )
}

export default AdminCreateOfficialGameScheduleStep
