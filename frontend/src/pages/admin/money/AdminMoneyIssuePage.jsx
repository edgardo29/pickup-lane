import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  Flag,
  RefreshCw,
  RotateCcw,
} from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth.js'
import '../../../styles/admin/AdminMoneySupport.css'
import {
  ContextSection,
  CreditSummary,
  CreditUsagesSection,
  EmptyState,
  MoneyIssueEventsSection,
  MoneyIssueSummary,
  PaymentSummary,
  RefundEventsSection,
  RefundSummary,
  SectionHeader,
} from './AdminMoneyDetailSections.jsx'
import {
  formatDateTime,
  formatStatus,
} from './adminMoneyFormatters.js'
import AdminWorkspaceLayout from '../shared/AdminWorkspaceLayout.jsx'
import {
  getAdminMoneyIssue,
  resolveAdminMoneyIssue,
  retryAdminMoneyIssueCredit,
  retryAdminMoneyRefund,
} from '../shared/adminApi.js'

const RESOLUTION_REASON_OPTIONS = [
  { label: 'Retried Successfully', value: 'retried_successfully' },
  { label: 'Provider Completed', value: 'provider_completed_no_action_required' },
  { label: 'Handled Externally', value: 'handled_externally' },
  { label: 'Invalid Issue', value: 'invalid_issue' },
  { label: 'Unable To Complete', value: 'unable_to_complete_documented' },
]
const UNCERTAIN_PROVIDER_REFUND_STATUSES = new Set(['processing', 'unknown'])
const RETRYABLE_REFUND_STATUSES = new Set(['failed', 'cancelled'])

function buildMoneyIssueIdempotencyKey(prefix, moneyIssueId) {
  const randomValue = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`

  return `${prefix}:${moneyIssueId}:${randomValue}`
}

function getIssueRetryKind(moneyIssue, refund) {
  if (!moneyIssue || moneyIssue.status !== 'open') {
    return null
  }
  if (
    moneyIssue.recommended_action_code === 'retry_refund'
    && moneyIssue.issue_type?.startsWith('refund_')
    && moneyIssue.target_refund_id
  ) {
    if (
      !refund
      || !RETRYABLE_REFUND_STATUSES.has(refund.refund_status)
      || UNCERTAIN_PROVIDER_REFUND_STATUSES.has(refund.provider_status)
    ) {
      return null
    }
    return 'refund'
  }
  if (
    (moneyIssue.recommended_action_code === 'retry_credit_restore'
      || moneyIssue.recommended_action_code === 'retry_credit_release')
    && (moneyIssue.issue_type === 'credit_restore_failed'
      || moneyIssue.issue_type === 'credit_release_failed')
  ) {
    return 'credit'
  }
  return null
}

function AdminMoneyIssuePage() {
  const { moneyIssueId } = useParams()
  const { currentUser } = useAuth()
  const [detail, setDetail] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [pageError, setPageError] = useState('')
  const [refreshCount, setRefreshCount] = useState(0)
  const [resolveForm, setResolveForm] = useState({
    externalReference: '',
    note: '',
    reasonCode: 'retried_successfully',
  })
  const [retryReason, setRetryReason] = useState('')
  const [retryStatus, setRetryStatus] = useState({
    error: '',
    message: '',
    state: 'idle',
  })
  const [resolveStatus, setResolveStatus] = useState({
    error: '',
    message: '',
    state: 'idle',
  })

  useEffect(() => {
    let isMounted = true

    async function loadMoneyIssue() {
      if (!currentUser || !moneyIssueId) {
        return
      }

      setLoadState('loading')
      setPageError('')

      try {
        const nextDetail = await getAdminMoneyIssue({
          firebaseUser: currentUser,
          moneyIssueId,
        })

        if (!isMounted) {
          return
        }

        setDetail(nextDetail)
        setLoadState('ready')
      } catch (error) {
        if (!isMounted) {
          return
        }

        setDetail(null)
        setPageError(error.message || 'Money issue could not be loaded.')
        setLoadState('error')
      }
    }

    loadMoneyIssue()

    return () => {
      isMounted = false
    }
  }, [currentUser, moneyIssueId, refreshCount])

  const pageTitle = useMemo(() => (
    detail?.money_issue
      ? `${formatStatus(detail.money_issue.status)} ${formatStatus(detail.money_issue.issue_type)}`
      : 'Money Issue'
  ), [detail])
  const retryKind = getIssueRetryKind(detail?.money_issue, detail?.refund)
  const canResolve = detail?.money_issue?.status === 'open'
  const retrySubmitting = retryStatus.state === 'submitting'
  const resolveSubmitting = resolveStatus.state === 'submitting'

  async function handleRetry(event) {
    event.preventDefault()

    const reason = retryReason.trim()
    if (!retryKind) {
      setRetryStatus({
        error: 'This issue is not retryable.',
        message: '',
        state: 'idle',
      })
      return
    }
    if (reason.length < 3) {
      setRetryStatus({
        error: 'Reason is required.',
        message: '',
        state: 'idle',
      })
      return
    }

    setRetryStatus({ error: '', message: '', state: 'submitting' })

    try {
      let nextDetail
      if (retryKind === 'refund') {
        await retryAdminMoneyRefund({
          firebaseUser: currentUser,
          refundId: detail.money_issue.target_refund_id,
          reason,
          idempotencyKey: buildMoneyIssueIdempotencyKey(
            'admin-money-refund-retry',
            detail.money_issue.target_refund_id,
          ),
        })
        nextDetail = await getAdminMoneyIssue({
          firebaseUser: currentUser,
          moneyIssueId,
        })
      } else {
        nextDetail = await retryAdminMoneyIssueCredit({
          firebaseUser: currentUser,
          moneyIssueId,
          reason,
          idempotencyKey: buildMoneyIssueIdempotencyKey(
            'admin-money-issue-credit-retry',
            moneyIssueId,
          ),
        })
      }

      setDetail(nextDetail)
      setRetryReason('')
      setRetryStatus({
        error: '',
        message: `${formatStatus(retryKind)} retry recorded.`,
        state: 'idle',
      })
    } catch (error) {
      setRetryStatus({
        error: error.message || 'Retry could not be recorded.',
        message: '',
        state: 'idle',
      })
    }
  }

  async function handleResolve(event) {
    event.preventDefault()

    const note = resolveForm.note.trim()
    const externalReference = resolveForm.externalReference.trim()
    if (!canResolve) {
      setResolveStatus({
        error: 'This money issue is already resolved.',
        message: '',
        state: 'idle',
      })
      return
    }
    if (
      resolveForm.reasonCode === 'handled_externally'
      && note.length < 3
    ) {
      setResolveStatus({
        error: 'Resolution note is required.',
        message: '',
        state: 'idle',
      })
      return
    }
    if (
      resolveForm.reasonCode === 'handled_externally'
      && externalReference.length < 3
    ) {
      setResolveStatus({
        error: 'External reference is required.',
        message: '',
        state: 'idle',
      })
      return
    }
    if (
      ['invalid_issue', 'unable_to_complete_documented'].includes(resolveForm.reasonCode)
      && note.length < 3
    ) {
      setResolveStatus({
        error: 'Resolution note is required.',
        message: '',
        state: 'idle',
      })
      return
    }

    setResolveStatus({ error: '', message: '', state: 'submitting' })

    try {
      const nextDetail = await resolveAdminMoneyIssue({
        firebaseUser: currentUser,
        moneyIssueId,
        reason: note,
        resolutionExternalReference: externalReference,
        resolutionReasonCode: resolveForm.reasonCode,
        idempotencyKey: buildMoneyIssueIdempotencyKey('admin-money-issue-resolve', moneyIssueId),
      })

      setDetail(nextDetail)
      setResolveForm({
        externalReference: '',
        note: '',
        reasonCode: 'retried_successfully',
      })
      setResolveStatus({
        error: '',
        message: 'Money issue resolved.',
        state: 'idle',
      })
    } catch (error) {
      setResolveStatus({
        error: error.message || 'Money issue could not be resolved.',
        message: '',
        state: 'idle',
      })
    }
  }

  return (
    <AdminWorkspaceLayout
      breadcrumbs={['Admin', 'Money', 'Money Issues']}
      description="Review this money issue and its related money records."
      icon={Flag}
      title={pageTitle}
    >
      <div className="admin-money-layout">
        <div className="admin-money-toolbar">
          <Link className="admin-money-button" to="/admin/money/issues">
            <ArrowLeft />
            Money Issues
          </Link>
          <button
            className="admin-money-button"
            type="button"
            onClick={() => setRefreshCount((count) => count + 1)}
          >
            <RefreshCw />
            Refresh
          </button>
        </div>

        {pageError && (
          <div className="admin-money-alert" role="alert">
            {pageError}
          </div>
        )}

        {loadState === 'loading' && (
          <section className="admin-money-panel">
            <EmptyState>Loading money issue.</EmptyState>
          </section>
        )}

        {loadState === 'ready' && detail && (
          <>
            <MoneyIssueSummary moneyIssue={detail.money_issue} />
            {retryKind && (
              <section className="admin-money-panel" aria-label="Retry money issue">
                <SectionHeader icon={RotateCcw} title={retryKind === 'refund' ? 'Retry Refund' : 'Retry Credit'} />
                <form className="admin-money-action-form" onSubmit={handleRetry}>
                  <label>
                    <span>Reason</span>
                    <textarea
                      disabled={retrySubmitting}
                      maxLength={1000}
                      onChange={(event) => setRetryReason(event.target.value)}
                      rows={3}
                      value={retryReason}
                    />
                  </label>
                  <div className="admin-money-action-bar">
                    <div className="admin-money-action-status">
                      {retryStatus.error && (
                        <p className="admin-money-form-error" role="alert">
                          {retryStatus.error}
                        </p>
                      )}
                      {retryStatus.message && (
                        <p className="admin-money-form-success" role="status">
                          {retryStatus.message}
                        </p>
                      )}
                    </div>
                    <button
                      className="admin-money-button admin-money-button--primary"
                      disabled={retrySubmitting}
                      type="submit"
                    >
                      <RotateCcw />
                      {retrySubmitting ? 'Retrying' : 'Retry'}
                    </button>
                  </div>
                </form>
              </section>
            )}
            <section className="admin-money-panel" aria-label="Resolve money issue">
              <SectionHeader icon={CheckCircle2} title="Resolve Issue" />
              {canResolve ? (
                <form className="admin-money-action-form" onSubmit={handleResolve}>
                  <label>
                    <span>Resolution</span>
                    <select
                      disabled={resolveSubmitting}
                      onChange={(event) => {
                        setResolveForm((current) => ({
                          ...current,
                          reasonCode: event.target.value,
                        }))
                      }}
                      value={resolveForm.reasonCode}
                    >
                      {RESOLUTION_REASON_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>External Reference</span>
                    <textarea
                      disabled={resolveSubmitting}
                      maxLength={255}
                      onChange={(event) => {
                        setResolveForm((current) => ({
                          ...current,
                          externalReference: event.target.value,
                        }))
                      }}
                      rows={2}
                      value={resolveForm.externalReference}
                    />
                  </label>
                  <label>
                    <span>Note</span>
                    <textarea
                      disabled={resolveSubmitting}
                      maxLength={1000}
                      onChange={(event) => {
                        setResolveForm((current) => ({
                          ...current,
                          note: event.target.value,
                        }))
                      }}
                      rows={3}
                      value={resolveForm.note}
                    />
                  </label>
                  <div className="admin-money-action-bar">
                    <div className="admin-money-action-status">
                      {resolveStatus.error && (
                        <p className="admin-money-form-error" role="alert">
                          {resolveStatus.error}
                        </p>
                      )}
                      {resolveStatus.message && (
                        <p className="admin-money-form-success" role="status">
                          {resolveStatus.message}
                        </p>
                      )}
                    </div>
                    <button
                      className="admin-money-button admin-money-button--primary"
                      disabled={resolveSubmitting}
                      type="submit"
                    >
                      <CheckCircle2 />
                      {resolveSubmitting ? 'Resolving' : 'Resolve Issue'}
                    </button>
                  </div>
                </form>
              ) : (
                <p className="admin-money-note">
                  {detail.money_issue.resolution_reason_code
                    ? `${formatStatus(detail.money_issue.resolution_reason_code)} on ${formatDateTime(detail.money_issue.resolved_at)}`
                    : 'This money issue is resolved.'}
                </p>
              )}
            </section>
            {detail.refund && <RefundSummary refund={detail.refund} />}
            {detail.payment && <PaymentSummary payment={detail.payment} />}
            {detail.credit && <CreditSummary credit={detail.credit} />}
            {(detail.credit_usages?.length ?? 0) > 0 && (
              <CreditUsagesSection creditUsages={detail.credit_usages ?? []} />
            )}
            <ContextSection booking={detail.booking} game={detail.game} />
            {detail.refund && (
              <RefundEventsSection refundEvents={detail.recent_refund_events ?? []} />
            )}
            <MoneyIssueEventsSection events={detail.events ?? []} />
          </>
        )}
      </div>
    </AdminWorkspaceLayout>
  )
}

export default AdminMoneyIssuePage
