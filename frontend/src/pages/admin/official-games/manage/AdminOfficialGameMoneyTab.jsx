import { Link } from 'react-router-dom'
import { formatAdminGameMoney } from '../shared/adminOfficialGameForm.js'
import {
  formatAdminDateTime,
  getCreditUsageTimelineLabel,
  getParticipantUserLabel,
  getPaymentTimelineLabel,
  getRefundTimelineLabel,
  getStatusLabel,
} from './adminOfficialGameManageDisplay.js'

const attentionPaymentStatuses = new Set(['processing', 'failed', 'disputed'])
const attentionRefundStatuses = new Set(['pending', 'approved', 'processing', 'failed'])

function AdminOfficialGameMoneyTab({
  error,
  game,
  loadState,
  moneyLedger,
  onRetry,
  participants,
}) {
  const payments = moneyLedger.payments ?? []
  const refunds = moneyLedger.refunds ?? []
  const credits = moneyLedger.credits ?? []
  const creditUsages = moneyLedger.credit_usages ?? []
  const paymentTotalCents = payments.reduce(
    (total, payment) => total + Number(payment.amount_cents || 0),
    0,
  )
  const refundTotalCents = refunds.reduce(
    (total, refund) => total + Number(refund.amount_cents || 0),
    0,
  )
  const creditUsageTotalCents = creditUsages.reduce(
    (total, usage) => total + Number(usage.amount_cents || 0),
    0,
  )
  const attentionCount = (
    payments.filter((payment) => attentionPaymentStatuses.has(payment.payment_status)).length
    + refunds.filter((refund) => attentionRefundStatuses.has(refund.refund_status)).length
  )
  const hasLedgerRows = (
    payments.length > 0
    || refunds.length > 0
    || credits.length > 0
    || creditUsages.length > 0
  )

  return (
    <section className="admin-official-panel admin-manage-tab-panel" aria-label="Official game money ledger">
      <div className="admin-manage-panel-heading">
        <div>
          <h2>Payments, Refunds, Credits</h2>
          <p>Read-only money ledger for this official game.</p>
        </div>
        <strong>{attentionCount}</strong>
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
        <p className="admin-official-empty">Loading money ledger.</p>
      )}

      {loadState === 'ready' && (
        <>
          <div className="admin-bookings-summary" aria-label="Money summary">
            <div>
              <span>Payments</span>
              <strong>
                {payments.length} / {formatAdminGameMoney(paymentTotalCents, game.currency)}
              </strong>
            </div>
            <div>
              <span>Refunds</span>
              <strong>
                {refunds.length} / {formatAdminGameMoney(refundTotalCents, game.currency)}
              </strong>
            </div>
            <div>
              <span>Credit grants</span>
              <strong>{credits.length}</strong>
            </div>
            <div>
              <span>Credit ledger</span>
              <strong>
                {creditUsages.length} / {formatAdminGameMoney(creditUsageTotalCents, game.currency)}
              </strong>
            </div>
          </div>

          {!hasLedgerRows && (
            <p className="admin-official-empty">No money ledger rows yet.</p>
          )}

          {payments.length > 0 && (
            <div className="admin-money-section">
              <h3>Payments</h3>
              <div className="admin-bookings-table admin-money-table" role="table" aria-label="Payments">
                <div className="admin-bookings-table__header" role="row">
                  <span role="columnheader">Payer</span>
                  <span role="columnheader">Payment</span>
                  <span role="columnheader">Amount</span>
                  <span role="columnheader">Status</span>
                  <span role="columnheader">Timeline</span>
                </div>
                {payments.map((payment) => (
                  <div key={payment.id} className="admin-bookings-table__row" role="row">
                    <div data-label="Payer" role="cell">
                      <strong>{getParticipantUserLabel(payment.payer_user_id, participants)}</strong>
                      <span>{String(payment.payer_user_id).slice(0, 8)}</span>
                    </div>
                    <div data-label="Payment" role="cell">
                      <Link className="admin-money-link" to={`/admin/money/payments/${payment.id}`}>
                        {getStatusLabel(payment.payment_type)}
                      </Link>
                      <span>{String(payment.id).slice(0, 8)}</span>
                    </div>
                    <div data-label="Amount" role="cell">
                      <strong>{formatAdminGameMoney(payment.amount_cents, payment.currency)}</strong>
                      <span>{payment.provider}</span>
                    </div>
                    <div data-label="Status" role="cell">
                      <strong>{getStatusLabel(payment.payment_status)}</strong>
                      <span>
                        {payment.failure_code
                          || payment.failure_reason
                          || payment.failure_message
                          || 'No failure'}
                      </span>
                    </div>
                    <div data-label="Timeline" role="cell">
                      <strong>{getPaymentTimelineLabel(payment)}</strong>
                      <span>{`Updated ${formatAdminDateTime(payment.updated_at)}`}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {refunds.length > 0 && (
            <div className="admin-money-section">
              <h3>Refunds</h3>
              <div className="admin-bookings-table admin-money-table" role="table" aria-label="Refunds">
                <div className="admin-bookings-table__header" role="row">
                  <span role="columnheader">Refund</span>
                  <span role="columnheader">Payment</span>
                  <span role="columnheader">Amount</span>
                  <span role="columnheader">Status</span>
                  <span role="columnheader">Timeline</span>
                </div>
                {refunds.map((refund) => (
                  <div key={refund.id} className="admin-bookings-table__row" role="row">
                    <div data-label="Refund" role="cell">
                      <Link className="admin-money-link" to={`/admin/money/refunds/${refund.id}`}>
                        {getStatusLabel(refund.refund_reason)}
                      </Link>
                      <span>{String(refund.id).slice(0, 8)}</span>
                    </div>
                    <div data-label="Payment" role="cell">
                      <strong>{String(refund.payment_id).slice(0, 8)}</strong>
                      <span>
                        {refund.booking_id
                          ? `Booking ${String(refund.booking_id).slice(0, 8)}`
                          : 'No booking'}
                      </span>
                    </div>
                    <div data-label="Amount" role="cell">
                      <strong>{formatAdminGameMoney(refund.amount_cents, refund.currency)}</strong>
                      <span>
                        {refund.provider_refund_id
                          ? 'Stripe refund linked'
                          : 'No Stripe refund id'}
                      </span>
                    </div>
                    <div data-label="Status" role="cell">
                      <strong>{getStatusLabel(refund.refund_status)}</strong>
                      <span>{refund.approved_by_user_id ? 'Approved by staff' : 'Not approved'}</span>
                    </div>
                    <div data-label="Timeline" role="cell">
                      <strong>{getRefundTimelineLabel(refund)}</strong>
                      <span>{`Updated ${formatAdminDateTime(refund.updated_at)}`}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(credits.length > 0 || creditUsages.length > 0) && (
            <div className="admin-money-section">
              <h3>Credits</h3>
              {credits.length > 0 && (
                <div className="admin-bookings-table admin-money-table" role="table" aria-label="Credit grants">
                  <div className="admin-bookings-table__header" role="row">
                    <span role="columnheader">User</span>
                    <span role="columnheader">Credit</span>
                    <span role="columnheader">Amount</span>
                    <span role="columnheader">Status</span>
                    <span role="columnheader">Timeline</span>
                  </div>
                  {credits.map((credit) => (
                    <div key={credit.id} className="admin-bookings-table__row" role="row">
                      <div data-label="User" role="cell">
                        <strong>{getParticipantUserLabel(credit.user_id, participants)}</strong>
                        <span>{String(credit.user_id).slice(0, 8)}</span>
                      </div>
                      <div data-label="Credit" role="cell">
                        <Link className="admin-money-link" to={`/admin/money/credits/${credit.id}`}>
                          {getStatusLabel(credit.credit_reason)}
                        </Link>
                        <span>{String(credit.id).slice(0, 8)}</span>
                      </div>
                      <div data-label="Amount" role="cell">
                        <strong>{formatAdminGameMoney(credit.amount_cents, credit.currency)}</strong>
                        <span>
                          {formatAdminGameMoney(credit.remaining_cents, credit.currency)} remaining
                        </span>
                      </div>
                      <div data-label="Status" role="cell">
                        <strong>{getStatusLabel(credit.credit_status)}</strong>
                        <span>{credit.reversed_at ? 'Reversed' : 'Not reversed'}</span>
                      </div>
                      <div data-label="Timeline" role="cell">
                        <strong>{`Created ${formatAdminDateTime(credit.created_at)}`}</strong>
                        <span>
                          {credit.expires_at
                            ? `Expires ${formatAdminDateTime(credit.expires_at)}`
                            : 'No expiry'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {creditUsages.length > 0 && (
                <div className="admin-bookings-table admin-money-table" role="table" aria-label="Credit usage">
                  <div className="admin-bookings-table__header" role="row">
                    <span role="columnheader">User</span>
                    <span role="columnheader">Usage</span>
                    <span role="columnheader">Amount</span>
                    <span role="columnheader">Status</span>
                    <span role="columnheader">Timeline</span>
                  </div>
                  {creditUsages.map((usage) => (
                    <div key={usage.id} className="admin-bookings-table__row" role="row">
                      <div data-label="User" role="cell">
                        <strong>{getParticipantUserLabel(usage.user_id, participants)}</strong>
                        <span>{String(usage.user_id).slice(0, 8)}</span>
                      </div>
                      <div data-label="Usage" role="cell">
                        <Link className="admin-money-link" to={`/admin/money/credits/${usage.game_credit_id}`}>
                          {getStatusLabel(usage.usage_type)}
                        </Link>
                        <span>{String(usage.id).slice(0, 8)}</span>
                      </div>
                      <div data-label="Amount" role="cell">
                        <strong>{formatAdminGameMoney(usage.amount_cents, usage.currency)}</strong>
                        <span>{usage.release_reason || 'No release reason'}</span>
                      </div>
                      <div data-label="Status" role="cell">
                        <strong>{getStatusLabel(usage.usage_status)}</strong>
                        <span>
                          {usage.booking_id
                            ? `Booking ${String(usage.booking_id).slice(0, 8)}`
                            : 'No booking'}
                        </span>
                      </div>
                      <div data-label="Timeline" role="cell">
                        <strong>{getCreditUsageTimelineLabel(usage)}</strong>
                        <span>{`Updated ${formatAdminDateTime(usage.updated_at)}`}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default AdminOfficialGameMoneyTab
