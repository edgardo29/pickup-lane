import { Link } from 'react-router-dom'
import {
  FileClock,
  ReceiptText,
} from 'lucide-react'
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
  getRefundRowTarget,
} from './adminMoneySectionSelectors.js'

export function RefundSummary({ providerSnapshot, refund }) {
  const provider = providerSnapshot || {
    provider: refund.provider,
    provider_charge_id: refund.provider_charge_id,
    provider_refund_id: refund.provider_refund_id,
    provider_status: refund.provider_status,
    provider_status_observed_at: refund.provider_status_observed_at,
  }

  return (
    <section className="admin-money-panel" aria-label="Refund summary">
      <SectionHeader icon={ReceiptText} title="Refund" />
      <div className="admin-money-kpis">
        <div>
          <span>Amount</span>
          <strong>{formatMoney(refund.amount_cents, refund.currency)}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{formatStatus(refund.refund_status)}</strong>
        </div>
        <div>
          <span>Reason</span>
          <strong>{formatStatus(refund.refund_reason)}</strong>
        </div>
        <div>
          <span>Provider Status</span>
          <strong>{formatStatus(provider.provider_status || 'unknown')}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Refund ID" value={refund.id} />
        <DetailCodeField label="Payment" value={refund.payment_id} />
        <DetailCodeField label="Booking" value={refund.booking_id} />
        <DetailCodeField label="Participant" value={refund.participant_id} />
        <DetailCodeField label="Publish fee" value={refund.host_publish_fee_id} />
        <DetailCodeField label="Provider refund" value={provider.provider_refund_id} />
        <DetailCodeField label="Provider charge" value={provider.provider_charge_id} />
        <DetailField label="Origin" value={formatStatus(refund.origin_workflow)} />
        <DetailField label="Provider" value={formatStatus(provider.provider)} />
        <DetailField label="Provider observed" value={formatDateTime(provider.provider_status_observed_at)} />
        <DetailField label="Requested" value={formatDateTime(refund.requested_at)} />
        <DetailField label="Approved" value={formatDateTime(refund.approved_at)} />
        <DetailField label="Refunded" value={formatDateTime(refund.refunded_at)} />
        <DetailField label="Last refund event" value={formatDateTime(refund.last_refund_event_at)} />
        <DetailField label="Created" value={formatDateTime(refund.created_at)} />
        <DetailField label="Updated" value={formatDateTime(refund.updated_at)} />
      </div>
    </section>
  )
}
export function RefundsSection({
  hasMore = false,
  refunds,
  showIssueContext = true,
  viewAllTo = '',
}) {
  return (
    <section className="admin-money-panel" aria-label="Refunds">
      <SectionHeader count={refunds.length} icon={ReceiptText} title="Refunds" />
      {refunds.length === 0 ? (
        <EmptyState>No refunds linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {refunds.map((refund) => (
            <div className="admin-money-row admin-money-row--four" key={refund.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/refunds/${refund.id}`}>
                  {formatStatus(refund.refund_status)}
                </Link>
                <span>{formatStatus(refund.refund_reason)}</span>
              </div>
              <div>
                <span>{formatMoney(refund.amount_cents, refund.currency)}</span>
                <span>
                  {refund.origin_workflow
                    ? formatStatus(refund.origin_workflow)
                    : getDisplayContext(refund)}
                </span>
              </div>
              <div>
                <span>{getRefundRowTarget(refund, showIssueContext)}</span>
                {showIssueContext && (
                  <span>
                    {refund.linked_issue || refund.linked_money_issue
                      ? 'Linked issue'
                      : 'No linked issue'}
                  </span>
                )}
              </div>
              <div>
                <span>{formatDateTime(refund.last_refund_event_at || refund.created_at)}</span>
                <code>{shortId(refund.id)}</code>
              </div>
            </div>
          ))}
          {hasMore && viewAllTo && (
            <div className="admin-money-row">
              <Link className="admin-money-row-link" to={viewAllTo}>View all refunds</Link>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
export function RefundEventsSection({ refundEvents }) {
  return (
    <section className="admin-money-panel" aria-label="Refund events">
      <SectionHeader count={refundEvents.length} icon={FileClock} title="Refund Events" />
      {refundEvents.length === 0 ? (
        <EmptyState>No refund events recorded.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {refundEvents.map((event) => (
            <div className="admin-money-row admin-money-row--four" key={event.id}>
              <div>
                <strong>{formatStatus(event.event_type)}</strong>
                <span>{event.summary || formatStatus(event.reason_code)}</span>
              </div>
              <div>
                <span>{formatStatus(event.new_refund_status || event.provider_status || 'unknown')}</span>
                <span>{formatStatus(event.event_source)}</span>
              </div>
              <div>
                <span>{formatStatus(event.reason_code)}</span>
                <code>{shortId(event.provider_refund_id || event.provider_charge_id)}</code>
              </div>
              <div>
                <span>{formatDateTime(event.occurred_at)}</span>
                <code>{shortId(event.id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
