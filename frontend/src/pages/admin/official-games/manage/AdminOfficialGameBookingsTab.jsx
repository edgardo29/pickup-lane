import { ClipboardListIcon, UserIcon } from '../../../../components/BrowseIcons.jsx'
import { formatAdminGameMoney } from '../shared/adminOfficialGameForm.js'
import AdminOfficialGameEmptyState from './AdminOfficialGameEmptyState.jsx'
import {
  formatAdminDateTime,
  getBookingBuyerLabel,
  getTitleLabel,
} from './adminOfficialGameManageDisplay.js'

function formatPartySize(count) {
  const partySize = Number(count || 0)
  return `${partySize} ${partySize === 1 ? 'player' : 'players'}`
}

function getBookingTimeline(booking) {
  if (booking.cancelled_at) {
    return {
      label: 'Cancelled',
      value: formatAdminDateTime(booking.cancelled_at),
    }
  }

  if (booking.expires_at) {
    return {
      label: 'Expires',
      value: formatAdminDateTime(booking.expires_at),
    }
  }

  if (booking.booked_at) {
    return {
      label: 'Booked',
      value: formatAdminDateTime(booking.booked_at),
    }
  }

  return {
    label: 'Created',
    value: formatAdminDateTime(booking.created_at),
  }
}

function BookingFact({ label, meta, value }) {
  return (
    <div className="admin-booking-card__fact">
      <span>{label}</span>
      <strong>{value}</strong>
      {meta && <small>{meta}</small>}
    </div>
  )
}

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
    <section className="admin-manage-tab-panel admin-bookings-panel" aria-label="Official game bookings">
      <div className="admin-manage-panel-heading admin-bookings-heading">
        <div className="admin-bookings-heading__copy">
          <span className="admin-bookings-heading__icon">
            <ClipboardListIcon />
          </span>
          <div>
            <h2>Bookings</h2>
            <p>Review booking status, payments, and party details.</p>
          </div>
        </div>
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
            <AdminOfficialGameEmptyState
              icon={ClipboardListIcon}
              title="No bookings yet"
            >
              Bookings will appear here after players reserve a spot.
            </AdminOfficialGameEmptyState>
          ) : (
            <div className="admin-booking-card-grid" aria-label="Bookings">
              {bookings.map((booking) => {
                const timeline = getBookingTimeline(booking)

                return (
                  <article className="admin-booking-card" key={booking.id}>
                    <header className="admin-booking-card__header">
                      <div className="admin-booking-card__buyer">
                        <UserIcon />
                        <span>
                          <small>Buyer</small>
                          <strong>{getBookingBuyerLabel(booking, participants)}</strong>
                          <em>Booking {String(booking.id).slice(0, 8)}</em>
                        </span>
                      </div>
                      <div className="admin-booking-card__total">
                        <small>Total</small>
                        <strong>{formatAdminGameMoney(booking.total_cents, booking.currency)}</strong>
                      </div>
                    </header>

                    <div className="admin-booking-card__facts">
                      <BookingFact
                        label="Booking"
                        value={getTitleLabel(booking.booking_status)}
                      />
                      <BookingFact
                        label="Payment"
                        meta={booking.currency}
                        value={getTitleLabel(booking.payment_status)}
                      />
                      <BookingFact
                        label="Party"
                        meta={`${formatAdminGameMoney(
                          booking.price_per_player_snapshot_cents,
                          booking.currency,
                        )} each`}
                        value={formatPartySize(booking.participant_count)}
                      />
                      <BookingFact
                        label="Timeline"
                        meta={timeline.value}
                        value={timeline.label}
                      />
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default AdminOfficialGameBookingsTab
