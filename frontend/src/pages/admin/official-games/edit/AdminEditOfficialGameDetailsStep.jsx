import {
  AddressIcon,
} from '../../../../components/GameFactIcons.jsx'
import {
  AdminCreateField,
  AdminCreateSectionLabel,
  AdminCreateStepHeading,
  AdminCreateTextarea,
  AdminCreateToggle,
} from '../create/AdminCreateOfficialGameControls.jsx'
import { adminEditOfficialGameFieldLimits } from './adminEditOfficialGameData.js'

function AdminEditOfficialGameDetailsStep({ form, updateField }) {
  return (
    <>
      <AdminCreateStepHeading
        title="Edit game details"
        text="Set booking controls, player instructions, and admin context."
      />

      <div className="admin-create-details-layout admin-edit-details-layout">
        <section className="admin-create-details-section admin-create-details-section--controls">
          <AdminCreateSectionLabel>Booking controls</AdminCreateSectionLabel>
          <div className="admin-create-details-grid">
            <AdminCreateField label="Max guests per booking">
              <select
                aria-label="Max guests per booking"
                value={form.maxGuestsPerBooking}
                onChange={(event) => updateField('maxGuestsPerBooking', Number(event.target.value))}
              >
                {[0, 1, 2].map((guestCount) => (
                  <option key={guestCount} value={guestCount}>
                    {guestCount}
                  </option>
                ))}
              </select>
            </AdminCreateField>

            <AdminCreateToggle
              checked={form.allowGuests}
              label="Guests"
              text="Allow players to include guests in their booking."
              onChange={(value) => updateField('allowGuests', value)}
            />
            <AdminCreateToggle
              checked={form.waitlistEnabled}
              label="Waitlist"
              text="Keep a queue when the game reaches capacity."
              onChange={(value) => updateField('waitlistEnabled', value)}
            />
            <AdminCreateToggle
              checked={form.isChatEnabled}
              label="Chat"
              text="Create a game chat for confirmed players."
              onChange={(value) => updateField('isChatEnabled', value)}
            />
          </div>
        </section>

        <section className="admin-create-details-section">
          <AdminCreateSectionLabel>Venue</AdminCreateSectionLabel>
          <div className="admin-edit-readonly-venue">
            <AddressIcon />
            <div>
              <strong>{form.venueName || 'Venue unavailable'}</strong>
              <span>{buildVenueLine(form)}</span>
            </div>
          </div>
        </section>

        <section className="admin-create-details-section">
          <AdminCreateSectionLabel>Notes</AdminCreateSectionLabel>
          <div className="admin-edit-notes-grid">
            <AdminCreateTextarea
              field="playerInstructions"
              form={form}
              label="Player instructions"
              maxLength={adminEditOfficialGameFieldLimits.playerInstructions}
              placeholder="Bring a white shirt and a dark shirt."
              updateField={updateField}
            />
            <AdminCreateTextarea
              field="parkingNotes"
              form={form}
              label="Parking note"
              maxLength={adminEditOfficialGameFieldLimits.parkingNotes}
              placeholder="Parking or arrival details"
              updateField={updateField}
            />
            <label className="admin-create-textarea-field admin-edit-reason-field">
              <span>Internal reason</span>
              <textarea
                maxLength={adminEditOfficialGameFieldLimits.reason}
                placeholder="Optional admin note for the audit log"
                value={form.reason}
                onChange={(event) => updateField('reason', event.target.value)}
              />
              <small>{form.reason.length}/{adminEditOfficialGameFieldLimits.reason}</small>
            </label>
          </div>
        </section>
      </div>
    </>
  )
}

function buildVenueLine(form) {
  return [
    form.addressLine1,
    [form.city, form.state].filter(Boolean).join(', '),
  ].filter(Boolean).join(' · ') || 'Location unavailable'
}

export default AdminEditOfficialGameDetailsStep
