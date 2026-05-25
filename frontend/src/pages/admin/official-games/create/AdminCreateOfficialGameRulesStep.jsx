import { UsersIcon } from '../../../../components/BrowseIcons.jsx'
import {
  AdminCreateField,
  AdminCreateSectionLabel,
  AdminCreateStepperInput,
  AdminCreateStepHeading,
  AdminCreateToggle,
} from './AdminCreateOfficialGameControls.jsx'

function AdminCreateOfficialGameRulesStep({ form, updateField }) {
  return (
    <>
      <AdminCreateStepHeading
        title="Official settings"
        text="Set the official booking controls."
      />

      <div className="admin-create-section">
        <AdminCreateSectionLabel>Official Controls</AdminCreateSectionLabel>
        <div className="admin-create-grid admin-create-grid--single">
          <AdminCreateField icon={<UsersIcon />} label="Max guests">
            <AdminCreateStepperInput
              ariaLabel="max guests"
              value={form.maxGuestsPerBooking}
              min={0}
              max={2}
              onChange={(value) => updateField('maxGuestsPerBooking', value)}
            />
          </AdminCreateField>
        </div>
      </div>

      <div className="admin-create-section">
        <AdminCreateSectionLabel>Availability</AdminCreateSectionLabel>
        <div className="admin-create-check-stack">
          <AdminCreateToggle
            checked={form.allowGuests}
            label="Guests"
            onChange={(value) => updateField('allowGuests', value)}
          />
          <AdminCreateToggle
            checked={form.waitlistEnabled}
            label="Waitlist"
            onChange={(value) => updateField('waitlistEnabled', value)}
          />
          <AdminCreateToggle
            checked={form.isChatEnabled}
            label="Chat"
            onChange={(value) => updateField('isChatEnabled', value)}
          />
        </div>
      </div>
    </>
  )
}

export default AdminCreateOfficialGameRulesStep
