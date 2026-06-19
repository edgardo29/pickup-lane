import { formatAdminGameMoney } from '../shared/adminOfficialGameForm.js'
import {
  formatAdminDateTime,
  getStatusLabel,
  getWaitlistTimelineLabel,
  getWaitlistUserLabel,
} from './adminOfficialGameManageDisplay.js'

const activeWaitlistStatuses = new Set(['active', 'payment_processing'])

function getWaitlistPaymentMethodLabel(entry) {
  if (entry.authorized_payment_method_brand && entry.authorized_payment_method_last4) {
    return `${entry.authorized_payment_method_brand} ending ${entry.authorized_payment_method_last4}`
  }
  return 'No saved card'
}

function AdminOfficialGameWaitlistTab({
  error,
  game,
  loadState,
  onRetry,
  participants,
  waitlistEntries,
}) {
  const activeEntries = waitlistEntries.filter((entry) =>
    activeWaitlistStatuses.has(entry.waitlist_status),
  )
  const activePartySize = activeEntries.reduce(
    (total, entry) => total + Number(entry.party_size || 0),
    0,
  )
  const authorizedEntryCount = waitlistEntries.filter((entry) =>
    Boolean(entry.auto_charge_consent_at && entry.authorized_payment_method_last4),
  ).length
  const authorizedAmountCents = waitlistEntries.reduce(
    (total, entry) => total + Number(entry.authorized_amount_cents || 0),
    0,
  )

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game waitlist">
      <div className="admin-manage-panel-heading">
        <div>
          <h2>Waitlist</h2>
          <p>Read-only waitlist ledger for this official game.</p>
        </div>
        <strong>{waitlistEntries.length}</strong>
      </div>

      {error && (
        <div className="admin-official-alert">
          <span>{error}</span>
          <button className="admin-official-button" type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}
      {loadState === 'loading' && (
        <p className="admin-official-empty">Loading waitlist.</p>
      )}

      {loadState === 'ready' && (
        <>
          <div className="admin-bookings-summary" aria-label="Waitlist summary">
            <div>
              <span>Total entries</span>
              <strong>{waitlistEntries.length}</strong>
            </div>
            <div>
              <span>Active entries</span>
              <strong>{activeEntries.length}</strong>
            </div>
            <div>
              <span>Active party size</span>
              <strong>{activePartySize}</strong>
            </div>
            <div>
              <span>Authorized</span>
              <strong>
                {authorizedEntryCount} / {formatAdminGameMoney(authorizedAmountCents, game.currency)}
              </strong>
            </div>
          </div>

          {waitlistEntries.length === 0 ? (
            <p className="admin-official-empty">No waitlist entries yet.</p>
          ) : (
            <div className="admin-bookings-table admin-waitlist-table" role="table" aria-label="Waitlist">
              <div className="admin-bookings-table__header" role="row">
                <span role="columnheader">Player</span>
                <span role="columnheader">Position</span>
                <span role="columnheader">Party</span>
                <span role="columnheader">Auto-charge</span>
                <span role="columnheader">Authorized</span>
                <span role="columnheader">Timeline</span>
              </div>
              {waitlistEntries.map((entry) => (
                <div key={entry.id} className="admin-bookings-table__row" role="row">
                  <div data-label="Player" role="cell">
                    <strong>{getWaitlistUserLabel(entry, participants)}</strong>
                    <span>{String(entry.id).slice(0, 8)}</span>
                  </div>
                  <div data-label="Position" role="cell">
                    <strong>#{entry.position}</strong>
                    <span>{getStatusLabel(entry.waitlist_status)}</span>
                  </div>
                  <div data-label="Party" role="cell">
                    <strong>{entry.party_size}</strong>
                    <span>
                      {entry.promoted_booking_id
                        ? 'Promoted booking linked'
                        : 'No promoted booking'}
                    </span>
                  </div>
                  <div data-label="Auto-charge" role="cell">
                    <strong>{getWaitlistPaymentMethodLabel(entry)}</strong>
                    <span>{entry.auto_charge_consent_version || 'No consent version'}</span>
                  </div>
                  <div data-label="Authorized" role="cell">
                    <strong>
                      {entry.authorized_amount_cents == null
                        ? 'None'
                        : formatAdminGameMoney(entry.authorized_amount_cents, game.currency)}
                    </strong>
                    <span>
                      {entry.auto_charge_consent_at
                        ? `Consented ${formatAdminDateTime(entry.auto_charge_consent_at)}`
                        : 'No consent timestamp'}
                    </span>
                  </div>
                  <div data-label="Timeline" role="cell">
                    <strong>{getWaitlistTimelineLabel(entry)}</strong>
                    <span>{`Updated ${formatAdminDateTime(entry.updated_at)}`}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default AdminOfficialGameWaitlistTab
