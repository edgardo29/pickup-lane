import { formatAdminGameMoney } from '../shared/adminOfficialGameForm.js'
import {
  formatAdminDateTime,
  getBookingBuyerLabel,
  getStatusLabel,
} from './adminOfficialGameManageDisplay.js'

function AdminOfficialGameBookingsTab({
  bookings,
  error,
  loadState,
  onRetry,
  participants,
}) {
  const totalBookedCents = bookings.reduce(
    (total, booking) => total + Number(booking.total_cents || 0),
    0,
  )
  const totalPartySize = bookings.reduce(
    (total, booking) => total + Number(booking.participant_count || 0),
    0,
  )
  const activeBookingCount = bookings.filter((booking) =>
    ['confirmed', 'pending_payment', 'waitlisted', 'partially_cancelled'].includes(
      booking.booking_status,
    ),
  ).length

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game bookings">
      <div className="admin-manage-panel-heading">
        <div>
          <h2>Bookings</h2>
          <p>Read-only booking ledger for this official game.</p>
        </div>
        <strong>{bookings.length}</strong>
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
        <p className="admin-official-empty">Loading bookings.</p>
      )}

      {loadState === 'ready' && (
        <>
          <div className="admin-bookings-summary" aria-label="Booking summary">
            <div>
              <span>Total bookings</span>
              <strong>{bookings.length}</strong>
            </div>
            <div>
              <span>Active bookings</span>
              <strong>{activeBookingCount}</strong>
            </div>
            <div>
              <span>Party size</span>
              <strong>{totalPartySize}</strong>
            </div>
            <div>
              <span>Booking total</span>
              <strong>{formatAdminGameMoney(totalBookedCents)}</strong>
            </div>
          </div>

          {bookings.length === 0 ? (
            <p className="admin-official-empty">No bookings yet.</p>
          ) : (
            <div className="admin-bookings-table" role="table" aria-label="Bookings">
              <div className="admin-bookings-table__header" role="row">
                <span role="columnheader">Buyer</span>
                <span role="columnheader">Booking</span>
                <span role="columnheader">Payment</span>
                <span role="columnheader">Party</span>
                <span role="columnheader">Total</span>
                <span role="columnheader">Timeline</span>
              </div>
              {bookings.map((booking) => (
                <div key={booking.id} className="admin-bookings-table__row" role="row">
                  <div data-label="Buyer" role="cell">
                    <strong>{getBookingBuyerLabel(booking, participants)}</strong>
                    <span>{String(booking.id).slice(0, 8)}</span>
                  </div>
                  <div data-label="Booking" role="cell">
                    <strong>{getStatusLabel(booking.booking_status)}</strong>
                    <span>
                      {booking.cancel_reason
                        ? getStatusLabel(booking.cancel_reason)
                        : 'No cancellation reason'}
                    </span>
                  </div>
                  <div data-label="Payment" role="cell">
                    <strong>{getStatusLabel(booking.payment_status)}</strong>
                    <span>{booking.currency}</span>
                  </div>
                  <div data-label="Party" role="cell">
                    <strong>{booking.participant_count}</strong>
                    <span>
                      {formatAdminGameMoney(
                        booking.price_per_player_snapshot_cents,
                        booking.currency,
                      )} each
                    </span>
                  </div>
                  <div data-label="Total" role="cell">
                    <strong>{formatAdminGameMoney(booking.total_cents, booking.currency)}</strong>
                    <span>
                      {booking.discount_cents > 0
                        ? `${formatAdminGameMoney(booking.discount_cents, booking.currency)} discount`
                        : 'No discount'}
                    </span>
                  </div>
                  <div data-label="Timeline" role="cell">
                    <strong>
                      {booking.booked_at
                        ? formatAdminDateTime(booking.booked_at)
                        : 'Not booked'}
                    </strong>
                    <span>
                      {booking.cancelled_at
                        ? `Cancelled ${formatAdminDateTime(booking.cancelled_at)}`
                        : booking.expires_at
                          ? `Expires ${formatAdminDateTime(booking.expires_at)}`
                          : `Created ${formatAdminDateTime(booking.created_at)}`}
                    </span>
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

export default AdminOfficialGameBookingsTab
