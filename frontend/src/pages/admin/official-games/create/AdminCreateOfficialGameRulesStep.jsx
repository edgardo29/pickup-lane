import {
  AdminCreateField,
  AdminCreateSectionLabel,
  AdminCreateStepHeading,
  AdminCreateToggle,
} from './AdminCreateOfficialGameControls.jsx'

function AdminCreateOfficialGameRulesStep({ form, updateField }) {
  return (
    <>
      <AdminCreateStepHeading
        title="Game details"
        text="Set guest access, waitlist availability, and game chat."
      />

      <div className="admin-create-details-layout">
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
      </div>
    </>
  )
}

export default AdminCreateOfficialGameRulesStep
