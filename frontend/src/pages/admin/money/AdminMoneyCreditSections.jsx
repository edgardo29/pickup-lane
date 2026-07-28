import { Link } from 'react-router-dom'
import { CircleDollarSign } from 'lucide-react'
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
import { getDisplayContext } from './adminMoneySectionSelectors.js'

export function CreditSummary({ credit }) {
  return (
    <section className="admin-money-panel" aria-label="Credit summary">
      <SectionHeader icon={CircleDollarSign} title="Credit" />
      <div className="admin-money-kpis">
        <div>
          <span>Original Amount</span>
          <strong>{formatMoney(credit.amount_cents, credit.currency)}</strong>
        </div>
        <div>
          <span>Available</span>
          <strong>{formatMoney(credit.available_cents, credit.currency)}</strong>
        </div>
        <div>
          <span>Reserved</span>
          <strong>{formatMoney(credit.reserved_cents ?? 0, credit.currency)}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{formatStatus(credit.credit_status)}</strong>
        </div>
        <div>
          <span>Reason</span>
          <strong>{formatStatus(credit.credit_reason)}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Credit ID" value={credit.id} />
        <DetailCodeField label="User" value={credit.user_id} />
        <DetailCodeField label="Source game" value={credit.source_game_id} />
        <DetailCodeField label="Source booking" value={credit.source_booking_id} />
        <DetailCodeField label="Source payment" value={credit.source_payment_id} />
        <DetailCodeField label="Issued by" value={credit.issued_by_user_id} />
        <DetailCodeField label="Reversed by" value={credit.reversed_by_user_id} />
        <DetailCodeField label="Idempotency" value={credit.idempotency_key} />
        <DetailField label="Note" value={credit.note} />
        <DetailField label="Reversed" value={formatDateTime(credit.reversed_at)} />
        <DetailField label="Created" value={formatDateTime(credit.created_at)} />
        <DetailField label="Updated" value={formatDateTime(credit.updated_at)} />
      </div>
    </section>
  )
}
export function CreditUsagesSection({
  creditUsageCount = 0,
  creditUsages,
  isTruncated = false,
}) {
  const displayCount = creditUsageCount || creditUsages.length

  return (
    <section className="admin-money-panel" aria-label="Credit usage ledger">
      <SectionHeader count={displayCount} icon={CircleDollarSign} title="Usage Ledger" />
      {creditUsages.length === 0 ? (
        <EmptyState>No usage ledger rows linked to this credit.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {isTruncated && (
            <div className="admin-money-row">
              <span>Showing the most recent {creditUsages.length} usage rows.</span>
            </div>
          )}
          {creditUsages.map((usage) => (
            <div className="admin-money-row admin-money-row--four" key={usage.id}>
              <div>
                <strong>{formatStatus(usage.usage_status)}</strong>
                <span>{formatStatus(usage.usage_type)}</span>
              </div>
              <div>
                <span>{formatMoney(usage.amount_cents, usage.currency)}</span>
                <span>{usage.reason_code || 'No reason code'}</span>
              </div>
              <div>
                <span>{usage.booking_id ? `Booking ${shortId(usage.booking_id)}` : 'No booking'}</span>
                <code>{shortId(usage.original_usage_id)}</code>
              </div>
              <div>
                <span>{formatDateTime(usage.updated_at)}</span>
                <code>{shortId(usage.id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
export function CreditsSection({ creditGrants, creditUsages, hasMore = false, viewAllTo = '' }) {
  const totalCount = creditGrants.length + creditUsages.length

  return (
    <section className="admin-money-panel" aria-label="Credits">
      <SectionHeader count={totalCount} icon={CircleDollarSign} title="Credits" />
      {totalCount === 0 ? (
        <EmptyState>No credit grant or usage rows linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {creditUsages.map((usage) => (
            <div className="admin-money-row admin-money-row--four" key={`usage-${usage.id}`}>
              <div>
                <strong>{formatStatus(usage.usage_status)}</strong>
                <span>{formatStatus(usage.usage_type)}</span>
              </div>
              <div>
                <span>{formatMoney(usage.amount_cents, usage.currency)}</span>
                <span>{usage.reason_code || 'No reason code'}</span>
              </div>
              <div>
                <span>{usage.booking_id ? `Booking ${shortId(usage.booking_id)}` : 'No booking'}</span>
                <code>{shortId(usage.game_credit_id)}</code>
              </div>
              <div>
                <span>{formatDateTime(usage.updated_at)}</span>
                <code>{shortId(usage.id)}</code>
              </div>
            </div>
          ))}
          {creditGrants.map((credit) => (
            <div className="admin-money-row admin-money-row--four" key={`credit-${credit.id}`}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/credits/${credit.id}`}>
                  {formatStatus(credit.credit_status)}
                </Link>
                <span>{formatStatus(credit.credit_reason)}</span>
              </div>
              <div>
                <span>{formatMoney(credit.amount_cents, credit.currency)}</span>
                <span>{formatMoney(credit.available_cents, credit.currency)} available</span>
              </div>
              <div>
                <span>{getDisplayContext(credit)}</span>
                <span>
                  {credit.open_money_issue_count === 1
                    ? '1 open issue'
                    : `${credit.open_money_issue_count} open issues`}
                </span>
              </div>
              <div>
                <span>{formatDateTime(credit.updated_at)}</span>
                <code>{shortId(credit.id)}</code>
              </div>
            </div>
          ))}
          {hasMore && viewAllTo && (
            <div className="admin-money-row">
              <Link className="admin-money-row-link" to={viewAllTo}>View all credits</Link>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
