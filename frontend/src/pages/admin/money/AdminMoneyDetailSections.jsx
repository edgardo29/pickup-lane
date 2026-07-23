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

export function SectionHeader({ count, icon: Icon, meta, title }) {
  const headerMeta = meta || (count !== undefined ? String(count) : '')

  return (
    <div className="admin-money-panel__heading">
      <div>
        <Icon />
        <h2>{title}</h2>
      </div>
      {headerMeta && <span className="admin-money-panel__meta">{headerMeta}</span>}
    </div>
  )
}

export function EmptyState({ children }) {
  return <p className="admin-money-empty">{children}</p>
}

function getDisplayContext(record) {
  const display = record?.display
  return record?.context_label
    || display?.context_label
    || display?.game_label
    || display?.user_email
    || display?.user_name
    || 'No context label'
}

function getPaymentRefundLabel(payment) {
  if (payment?.is_fully_refunded) {
    return 'Fully refunded'
  }

  return 'Not fully refunded'
}

function getPaymentRefundSummary(payment) {
  return getPaymentRefundLabel(payment)
}

function getRefundRowTarget(refund, showIssueContext) {
  if (showIssueContext) {
    return getDisplayContext(refund)
  }

  return refund?.payment_id
    ? `Payment ${shortId(refund.payment_id)}`
    : getDisplayContext(refund)
}

function getIssueTargetLabel(issue) {
  const target = [
    ['Payment', issue?.target_payment_id],
    ['Refund', issue?.target_refund_id],
    ['Credit', issue?.target_game_credit_id],
    ['Usage', issue?.target_credit_usage_id],
  ].find(([, value]) => Boolean(value))

  if (!target) {
    return 'No target'
  }

  return `${target[0]} ${shortId(target[1])}`
}

function getUserName(user) {
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(' ')
  return fullName || user?.email || 'User'
}

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

export function ContextSection({
  booking,
  communityPublishAttempt,
  game,
  hostPublishFee,
  participant,
  publishHost,
  userSummary,
}) {
  const canOpenOfficialGame = game?.game_type === 'official'
  if (
    !booking
    && !game
    && !hostPublishFee
    && !communityPublishAttempt
    && !participant
    && !publishHost
    && !userSummary
  ) {
    return null
  }

  return (
    <section className="admin-money-panel" aria-label="Money context">
      <SectionHeader icon={ShieldCheck} title="Context" />
      <div className="admin-money-context">
        {game && (
          <div>
            <h3>Game</h3>
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
          </div>
        )}
        {booking && (
          <div>
            <h3>Booking</h3>
            <>
              <strong>{formatStatus(booking.booking_status)}</strong>
              <span>{formatStatus(booking.payment_status)}</span>
              <span>{booking.participant_count} players</span>
              <span>{formatMoney(booking.total_cents, booking.currency)}</span>
            </>
          </div>
        )}
        {participant && (
          <div>
            <h3>Participant</h3>
            <>
              <strong>{participant.display_name_snapshot}</strong>
              <span>{formatStatus(participant.participant_status)}</span>
              <span>{formatStatus(participant.participant_type)}</span>
              <span>{formatMoney(participant.price_cents, participant.currency)}</span>
            </>
          </div>
        )}
        {hostPublishFee && (
          <div>
            <h3>Publish Fee</h3>
            <>
              <strong>{formatMoney(hostPublishFee.amount_cents, hostPublishFee.currency)}</strong>
              <span>{formatStatus(hostPublishFee.fee_status)}</span>
              <span>{formatStatus(hostPublishFee.waiver_reason)}</span>
              <code>{shortId(hostPublishFee.id)}</code>
            </>
          </div>
        )}
        {communityPublishAttempt && (
          <div>
            <h3>Publish Attempt</h3>
            <>
              <strong>{formatStatus(communityPublishAttempt.attempt_status)}</strong>
              <span>{formatMoney(communityPublishAttempt.amount_cents, communityPublishAttempt.currency)}</span>
              <span>{communityPublishAttempt.starts_on_local || 'No start date'}</span>
              <code>{shortId(communityPublishAttempt.id)}</code>
            </>
          </div>
        )}
        {publishHost && (
          <div>
            <h3>Host</h3>
            <>
              <strong>{getUserName(publishHost)}</strong>
              <span>{publishHost.email || 'No email'}</span>
              <span>{formatStatus(publishHost.account_status)}</span>
              <Link to={`/admin/users/${publishHost.id}`}>Open user</Link>
            </>
          </div>
        )}
        {userSummary && (
          <div>
            <h3>User</h3>
            <>
              <strong>{getUserName(userSummary)}</strong>
              <span>{userSummary.email || 'No email'}</span>
              <span>{formatStatus(userSummary.account_status)}</span>
              <Link to={`/admin/users/${userSummary.id}`}>Open user</Link>
            </>
          </div>
        )}
      </div>
    </section>
  )
}

export function MoneyIssueSummary({ moneyIssue }) {
  return (
    <section className="admin-money-panel" aria-label="Money issue summary">
      <SectionHeader icon={Flag} title="Money Issue" />
      <div className="admin-money-kpis">
        <div>
          <span>Status</span>
          <strong>{formatStatus(moneyIssue.status)}</strong>
        </div>
        <div>
          <span>Type</span>
          <strong>{formatStatus(moneyIssue.issue_type)}</strong>
        </div>
        <div>
          <span>Value</span>
          <strong>{formatMoney(moneyIssue.amount_cents, moneyIssue.currency)}</strong>
        </div>
        <div>
          <span>Action</span>
          <strong>{formatStatus(moneyIssue.recommended_action_code)}</strong>
        </div>
      </div>
      <div className="admin-money-field-grid">
        <DetailCodeField label="Issue ID" value={moneyIssue.id} />
        <DetailCodeField label="Operation key" value={moneyIssue.operation_key} />
        <DetailCodeField label="Target user" value={moneyIssue.target_user_id} />
        <DetailCodeField label="Target game" value={moneyIssue.target_game_id} />
        <DetailCodeField label="Target booking" value={moneyIssue.target_booking_id} />
        <DetailCodeField label="Target payment" value={moneyIssue.target_payment_id} />
        <DetailCodeField label="Target refund" value={moneyIssue.target_refund_id} />
        <DetailCodeField label="Target credit" value={moneyIssue.target_game_credit_id} />
        <DetailCodeField label="Target usage" value={moneyIssue.target_credit_usage_id} />
        <DetailField label="Origin" value={formatStatus(moneyIssue.origin_workflow)} />
        <DetailField label="Reason" value={formatStatus(moneyIssue.latest_reason_code)} />
        <DetailField label="Summary" value={moneyIssue.latest_summary} />
        <DetailField label="Occurrences" value={String(moneyIssue.occurrence_count)} />
        <DetailField label="Reopens" value={String(moneyIssue.reopen_count)} />
        <DetailField label="First detected" value={formatDateTime(moneyIssue.first_detected_at)} />
        <DetailField label="Last detected" value={formatDateTime(moneyIssue.last_detected_at)} />
        <DetailField label="Last activity" value={formatDateTime(moneyIssue.last_activity_at || moneyIssue.last_detected_at)} />
        <DetailField label="Resolved" value={formatDateTime(moneyIssue.resolved_at)} />
        <DetailField label="Resolution reason" value={formatStatus(moneyIssue.resolution_reason_code)} />
        <DetailField label="Resolution note" value={moneyIssue.resolution_note} />
        <DetailField label="External reference" value={moneyIssue.resolution_external_reference} />
      </div>
    </section>
  )
}

export function MoneyIssuesSection({ hasMore = false, moneyIssues, viewAllTo = '' }) {
  return (
    <section className="admin-money-panel" aria-label="Money issues">
      <SectionHeader count={moneyIssues.length} icon={Flag} title="Money Issues" />
      {moneyIssues.length === 0 ? (
        <EmptyState>No money issues linked here.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {moneyIssues.map((issue) => (
            <div className="admin-money-row admin-money-row--four" key={issue.id}>
              <div>
                <Link className="admin-money-row-link" to={`/admin/money/issues/${issue.id}`}>
                  {formatStatus(issue.issue_type)}
                </Link>
                <span>{issue.latest_summary || formatStatus(issue.latest_reason_code)}</span>
              </div>
              <div>
                <span>{formatMoney(issue.amount_cents, issue.currency)}</span>
                <span>{formatStatus(issue.status)}</span>
              </div>
              <div>
                <span>{formatStatus(issue.recommended_action_code)}</span>
                <span>{formatStatus(issue.origin_workflow)}</span>
              </div>
              <div>
                <span>Activity {formatDateTime(issue.last_activity_at || issue.last_detected_at)}</span>
                <span>{getIssueTargetLabel(issue)}</span>
              </div>
            </div>
          ))}
          {hasMore && viewAllTo && (
            <div className="admin-money-row">
              <Link className="admin-money-row-link" to={viewAllTo}>View all money issues</Link>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export function MoneyIssueEventsSection({ events }) {
  return (
    <section className="admin-money-panel" aria-label="Money issue events">
      <SectionHeader count={events.length} icon={FileClock} title="Issue Events" />
      {events.length === 0 ? (
        <EmptyState>No money issue events recorded.</EmptyState>
      ) : (
        <div className="admin-money-row-list">
          {events.map((event) => (
            <div className="admin-money-row admin-money-row--four" key={event.id}>
              <div>
                <strong>{formatStatus(event.event_type)}</strong>
                <span>{event.summary || formatStatus(event.reason_code)}</span>
              </div>
              <div>
                <span>{formatStatus(event.new_status || event.event_source)}</span>
                <span>{formatStatus(event.reason_code)}</span>
              </div>
              <div>
                <span>{formatStatus(event.new_issue_type || event.previous_issue_type)}</span>
                <code>{shortId(event.refund_event_id || event.result_credit_usage_id)}</code>
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

export function AuditSection({ auditActions }) {
  return (
    <section className="admin-money-panel" aria-label="Admin actions">
      <SectionHeader count={auditActions.length} icon={FileClock} title="Admin Actions" />
      {auditActions.length === 0 ? (
        <EmptyState>No directly relevant admin actions linked here.</EmptyState>
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
