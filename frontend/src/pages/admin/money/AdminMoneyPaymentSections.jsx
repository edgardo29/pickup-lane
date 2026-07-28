import { Link } from 'react-router-dom'
import { WalletCards } from 'lucide-react'
import {
  formatDateTime,
  formatMoney,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'
import {
  DetailCodeField,
  DetailField,
  EmptyState,
  SectionHeader,
} from './AdminMoneyDetailShared.jsx'
import {
  getDisplayContext,
  getPaymentRefundLabel,
  getPaymentRefundSummary,
  getUserName,
} from './adminMoneySectionSelectors.js'

export function PaymentSummary({ payer, payment }) {
  const payerLabel = payer
    ? getUserName(payer)
    : payment.display?.user_name || payment.display?.user_email || ''
  const payerEmail = payer?.email || payment.display?.user_email || ''

  return (
    <section className="admin-money-panel" aria-label="Payment summary">
      <SectionHeader icon={WalletCards} title="Payment" />
      <div className="admin-money-kpis">
        <div>
          <span>Amount</span>
          <strong>{formatMoney(payment.amount_cents, payment.currency)}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{formatStatus(payment.payment_status)}</strong>
        </div>
        <div>
          <span>Type</span>
          <strong>{formatStatus(payment.payment_type)}</strong>
        </div>
        <div>
          <span>Refund</span>
          <strong>{getPaymentRefundLabel(payment)}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Payment ID" value={payment.id} />
        <DetailField label="Payer" value={payerLabel} />
        <DetailField label="Payer email" value={payerEmail} />
        <DetailCodeField label="Payer user" value={payment.payer_user_id} />
        <DetailCodeField label="Booking" value={payment.booking_id} />
        <DetailCodeField label="Game" value={payment.game_id} />
        <DetailCodeField label="PaymentIntent" value={payment.provider_payment_intent_id} />
        <DetailCodeField label="Charge" value={payment.provider_charge_id} />
        <DetailCodeField label="Idempotency" value={payment.idempotency_key} />
        <DetailField label="Provider" value={formatStatus(payment.provider)} />
        <DetailField label="Paid" value={formatDateTime(payment.paid_at)} />
        <DetailField label="Created" value={formatDateTime(payment.created_at)} />
        <DetailField label="Updated" value={formatDateTime(payment.updated_at)} />
        <DetailField
          label="Failure"
          value={payment.failure_code || payment.failure_message || 'No failure recorded'}
        />
      </div>
    </section>
  )
}
export function PaymentsSection({
  hasMore = false,
  payments,
  showIssueContext = true,
  viewAllTo = '',
}) {
  return (
    <section className="admin-money-panel" aria-label="Payments">
      <SectionHeader count={payments.length} icon={WalletCards} title="Payments" />
      {payments.length === 0 ? (
        <EmptyState>No payments linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {payments.map((payment) => (
            <div className="admin-money-row admin-money-row--four" key={payment.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/payments/${payment.id}`}>
                  {formatStatus(payment.payment_status)}
                </Link>
                <span>{formatStatus(payment.payment_type)}</span>
              </div>
              <div>
                <span>{formatMoney(payment.amount_cents, payment.currency)}</span>
                <span>{getPaymentRefundSummary(payment)}</span>
              </div>
              <div>
                <span>{getDisplayContext(payment)}</span>
                {showIssueContext && (
                  <span>
                    {payment.open_money_issue_count
                      ? `${payment.open_money_issue_count} open issue`
                      : 'No open issue'}
                  </span>
                )}
              </div>
              <div>
                <span>{formatDateTime(payment.created_at)}</span>
                <code>{shortId(payment.id)}</code>
              </div>
            </div>
          ))}
          {hasMore && viewAllTo && (
            <div className="admin-money-row">
              <Link className="admin-money-row-link" to={viewAllTo}>View all payments</Link>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
