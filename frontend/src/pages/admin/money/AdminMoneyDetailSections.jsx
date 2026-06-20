import { Link } from 'react-router-dom'
import {
  CircleDollarSign,
  FileClock,
  Flag,
  ReceiptText,
  ShieldCheck,
  WalletCards,
} from 'lucide-react'
import {
  formatDateTime,
  formatMoney,
  formatStatus,
  shortId,
} from './adminMoneyFormatters.js'

export function DetailField({ label, value }) {
  return (
    <div className="admin-money-field">
      <span>{label}</span>
      <strong>{value || 'None'}</strong>
    </div>
  )
}

export function DetailCodeField({ label, value }) {
  return (
    <div className="admin-money-field">
      <span>{label}</span>
      <code>{value || 'None'}</code>
    </div>
  )
}

export function SectionHeader({ count, icon: Icon, title }) {
  return (
    <div className="admin-money-panel__heading">
      <div>
        <Icon />
        <h2>{title}</h2>
      </div>
      {count !== undefined && <em>{count}</em>}
    </div>
  )
}

export function EmptyState({ children }) {
  return <p className="admin-money-empty">{children}</p>
}

export function PaymentSummary({ payment }) {
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
          <span>Provider</span>
          <strong>{payment.provider}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Payment ID" value={payment.id} />
        <DetailCodeField label="Payer user" value={payment.payer_user_id} />
        <DetailCodeField label="Booking" value={payment.booking_id} />
        <DetailCodeField label="Game" value={payment.game_id} />
        <DetailCodeField label="PaymentIntent" value={payment.provider_payment_intent_id} />
        <DetailCodeField label="Charge" value={payment.provider_charge_id} />
        <DetailField label="Paid" value={formatDateTime(payment.paid_at)} />
        <DetailField label="Created" value={formatDateTime(payment.created_at)} />
        <DetailField label="Updated" value={formatDateTime(payment.updated_at)} />
        <DetailField
          label="Failure"
          value={payment.failure_code || payment.failure_reason || payment.failure_message || 'No failure recorded'}
        />
      </div>
    </section>
  )
}

export function PaymentsSection({ payments }) {
  return (
    <section className="admin-money-panel" aria-label="Payments">
      <SectionHeader count={payments.length} icon={WalletCards} title="Payments" />
      {payments.length === 0 ? (
        <EmptyState>No payments linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {payments.map((payment) => (
            <div className="admin-money-row" key={payment.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/payments/${payment.id}`}>
                  {formatStatus(payment.payment_status)}
                </Link>
                <span>{formatStatus(payment.payment_type)}</span>
              </div>
              <div>
                <span>{formatMoney(payment.amount_cents, payment.currency)}</span>
                <code>{shortId(payment.id)}</code>
              </div>
              <div>
                <span>{payment.provider_charge_id ? 'Stripe charge linked' : 'No Stripe charge id'}</span>
                <span>{formatDateTime(payment.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export function RefundSummary({ refund }) {
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
          <span>Provider</span>
          <strong>{refund.provider_refund_id ? 'Stripe' : 'No provider id'}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Refund ID" value={refund.id} />
        <DetailCodeField label="Payment" value={refund.payment_id} />
        <DetailCodeField label="Booking" value={refund.booking_id} />
        <DetailCodeField label="Participant" value={refund.participant_id} />
        <DetailCodeField label="Stripe refund" value={refund.provider_refund_id} />
        <DetailCodeField label="Requested by" value={refund.requested_by_user_id} />
        <DetailCodeField label="Approved by" value={refund.approved_by_user_id} />
        <DetailField label="Requested" value={formatDateTime(refund.requested_at)} />
        <DetailField label="Approved" value={formatDateTime(refund.approved_at)} />
        <DetailField label="Refunded" value={formatDateTime(refund.refunded_at)} />
        <DetailField label="Created" value={formatDateTime(refund.created_at)} />
        <DetailField label="Updated" value={formatDateTime(refund.updated_at)} />
      </div>
    </section>
  )
}

export function RefundsSection({ refunds }) {
  return (
    <section className="admin-money-panel" aria-label="Refunds">
      <SectionHeader count={refunds.length} icon={ReceiptText} title="Refunds" />
      {refunds.length === 0 ? (
        <EmptyState>No refunds linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {refunds.map((refund) => (
            <div className="admin-money-row" key={refund.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/refunds/${refund.id}`}>
                  {formatStatus(refund.refund_status)}
                </Link>
                <span>{formatStatus(refund.refund_reason)}</span>
              </div>
              <div>
                <span>{formatMoney(refund.amount_cents, refund.currency)}</span>
                <code>{shortId(refund.id)}</code>
              </div>
              <div>
                <span>{refund.provider_refund_id ? 'Stripe refund linked' : 'No Stripe refund id'}</span>
                <span>{formatDateTime(refund.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export function ContextSection({ booking, game }) {
  const canOpenOfficialGame = game?.game_type === 'official'

  return (
    <section className="admin-money-panel" aria-label="Money context">
      <SectionHeader icon={ShieldCheck} title="Context" />
      <div className="admin-money-context">
        <div>
          <h3>Game</h3>
          {game ? (
            <>
              <strong>{game.title}</strong>
              <span>{game.venue_name_snapshot}</span>
              <span>{formatDateTime(game.starts_at)}</span>
              {canOpenOfficialGame ? (
                <Link to={`/admin/official-games/${game.id}`}>Open official game</Link>
              ) : (
                <span>{formatStatus(game.game_type)} game</span>
              )}
            </>
          ) : (
            <EmptyState>No game context.</EmptyState>
          )}
        </div>
        <div>
          <h3>Booking</h3>
          {booking ? (
            <>
              <strong>{formatStatus(booking.booking_status)}</strong>
              <span>{formatStatus(booking.payment_status)}</span>
              <span>{booking.participant_count} players</span>
              <span>{formatMoney(booking.total_cents, booking.currency)}</span>
            </>
          ) : (
            <EmptyState>No booking context.</EmptyState>
          )}
        </div>
      </div>
    </section>
  )
}

export function SupportFlagSummary({ supportFlag }) {
  return (
    <section className="admin-money-panel" aria-label="Support flag summary">
      <SectionHeader icon={Flag} title="Support Flag" />
      <div className="admin-money-kpis">
        <div>
          <span>Status</span>
          <strong>{formatStatus(supportFlag.flag_status)}</strong>
        </div>
        <div>
          <span>Severity</span>
          <strong>{formatStatus(supportFlag.severity)}</strong>
        </div>
        <div>
          <span>Type</span>
          <strong>{formatStatus(supportFlag.flag_type)}</strong>
        </div>
        <div>
          <span>Source</span>
          <strong>{formatStatus(supportFlag.source)}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Support flag ID" value={supportFlag.id} />
        <DetailCodeField label="Target user" value={supportFlag.target_user_id} />
        <DetailCodeField label="Target game" value={supportFlag.target_game_id} />
        <DetailCodeField label="Target booking" value={supportFlag.target_booking_id} />
        <DetailCodeField label="Target payment" value={supportFlag.target_payment_id} />
        <DetailCodeField label="Target refund" value={supportFlag.target_refund_id} />
        <DetailCodeField label="Target credit" value={supportFlag.target_game_credit_id} />
        <DetailCodeField label="Source action" value={supportFlag.source_admin_action_id} />
        <DetailField label="Title" value={supportFlag.title} />
        <DetailField label="Summary" value={supportFlag.summary} />
        <DetailField
          label="Resolution"
          value={supportFlag.resolution_outcome ? formatStatus(supportFlag.resolution_outcome) : 'Unresolved'}
        />
        <DetailField label="Resolved" value={formatDateTime(supportFlag.resolved_at)} />
        <DetailField label="Created" value={formatDateTime(supportFlag.created_at)} />
        <DetailField label="Updated" value={formatDateTime(supportFlag.updated_at)} />
      </div>
    </section>
  )
}

export function CreditSummary({ credit }) {
  return (
    <section className="admin-money-panel" aria-label="Credit summary">
      <SectionHeader icon={CircleDollarSign} title="Credit" />
      <div className="admin-money-kpis">
        <div>
          <span>Amount</span>
          <strong>{formatMoney(credit.amount_cents, credit.currency)}</strong>
        </div>
        <div>
          <span>Remaining</span>
          <strong>{formatMoney(credit.remaining_cents, credit.currency)}</strong>
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
        <DetailField label="Expires" value={formatDateTime(credit.expires_at)} />
        <DetailField label="Reversed" value={formatDateTime(credit.reversed_at)} />
        <DetailField label="Created" value={formatDateTime(credit.created_at)} />
        <DetailField label="Updated" value={formatDateTime(credit.updated_at)} />
      </div>
    </section>
  )
}

export function CreditUsagesSection({ creditUsages }) {
  return (
    <section className="admin-money-panel" aria-label="Credit usage ledger">
      <SectionHeader count={creditUsages.length} icon={CircleDollarSign} title="Usage Ledger" />
      {creditUsages.length === 0 ? (
        <EmptyState>No usage ledger rows linked to this credit.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {creditUsages.map((usage) => (
            <div className="admin-money-row" key={usage.id}>
              <div>
                <strong>{formatStatus(usage.usage_status)}</strong>
                <span>{formatStatus(usage.usage_type)}</span>
              </div>
              <div>
                <span>{formatMoney(usage.amount_cents, usage.currency)}</span>
                <code>{shortId(usage.id)}</code>
              </div>
              <div>
                <span>{usage.release_reason || 'No release reason'}</span>
                <span>{formatDateTime(usage.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export function CreditsSection({ creditGrants, creditUsages }) {
  const totalCount = creditGrants.length + creditUsages.length

  return (
    <section className="admin-money-panel" aria-label="Credits">
      <SectionHeader count={totalCount} icon={CircleDollarSign} title="Credits" />
      {totalCount === 0 ? (
        <EmptyState>No credit grant or usage rows linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {creditUsages.map((usage) => (
            <div className="admin-money-row" key={`usage-${usage.id}`}>
              <div>
                <strong>{formatStatus(usage.usage_status)}</strong>
                <span>{formatStatus(usage.usage_type)}</span>
              </div>
              <div>
                <span>{formatMoney(usage.amount_cents, usage.currency)}</span>
                <code>{shortId(usage.id)}</code>
              </div>
              <div>
                <span>{usage.release_reason || 'No release reason'}</span>
                <span>{formatDateTime(usage.updated_at)}</span>
              </div>
            </div>
          ))}
          {creditGrants.map((credit) => (
            <div className="admin-money-row" key={`credit-${credit.id}`}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/credits/${credit.id}`}>
                  {formatStatus(credit.credit_status)}
                </Link>
                <span>{formatStatus(credit.credit_reason)}</span>
              </div>
              <div>
                <span>{formatMoney(credit.amount_cents, credit.currency)}</span>
                <code>{shortId(credit.id)}</code>
              </div>
              <div>
                <span>{formatMoney(credit.remaining_cents, credit.currency)} remaining</span>
                <span>{formatDateTime(credit.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export function SupportFlagsSection({ supportFlags }) {
  return (
    <section className="admin-money-panel" aria-label="Support flags">
      <SectionHeader count={supportFlags.length} icon={Flag} title="Support Flags" />
      {supportFlags.length === 0 ? (
        <EmptyState>No support flags linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {supportFlags.map((flag) => (
            <div className="admin-money-row" key={flag.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/support-flags/${flag.id}`}>
                  {flag.title}
                </Link>
                <span>{formatStatus(flag.flag_type)}</span>
              </div>
              <div>
                <span>{formatStatus(flag.flag_status)}</span>
                <em>{flag.severity}</em>
              </div>
              <div>
                <span>{flag.resolution_outcome ? formatStatus(flag.resolution_outcome) : 'Unresolved'}</span>
                <span>{formatDateTime(flag.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export function AuditSection({ auditActions }) {
  return (
    <section className="admin-money-panel" aria-label="Audit actions">
      <SectionHeader count={auditActions.length} icon={FileClock} title="Audit" />
      {auditActions.length === 0 ? (
        <EmptyState>No readable audit rows linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {auditActions.map((action) => (
            <div className="admin-money-row" key={action.id}>
              <div>
                <strong>{formatStatus(action.action_type)}</strong>
                <span>{action.reason || 'No reason recorded'}</span>
              </div>
              <div>
                <span>{formatDateTime(action.created_at)}</span>
                <code>{shortId(action.id)}</code>
              </div>
              <div>
                <span>Admin</span>
                <code>{shortId(action.admin_user_id)}</code>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
