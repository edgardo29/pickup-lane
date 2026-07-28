import { Link } from 'react-router-dom'
import {
  FileClock,
  Flag,
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
import { getIssueTargetLabel } from './adminMoneySectionSelectors.js'

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
